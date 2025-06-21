# transport/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)


class TrackingConsumer(AsyncWebsocketConsumer):
    """WebSocket pour le suivi en temps réel des livraisons"""
    
    async def connect(self):
        self.mission_id = self.scope['url_route']['kwargs']['mission_id']
        self.room_group_name = f'tracking_{self.mission_id}'
        
        # Vérifier l'authentification
        if self.scope["user"] == AnonymousUser():
            await self.close()
            return
        
        # Vérifier les permissions
        if not await self.check_permission():
            await self.close()
            return
        
        # Rejoindre le groupe
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer la position initiale
        await self.send_initial_position()
    
    async def disconnect(self, close_code):
        # Quitter le groupe
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Recevoir les mises à jour de position du transporteur"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'position_update':
                await self.handle_position_update(data)
            elif message_type == 'status_update':
                await self.handle_status_update(data)
            elif message_type == 'incident':
                await self.handle_incident(data)
                
        except json.JSONDecodeError:
            await self.send_error("Format de message invalide")
        except Exception as e:
            logger.error(f"Erreur update position: {e}")
    
    @database_sync_to_async
    def update_mission_status(self, new_status):
        """Mettre à jour le statut de la mission"""
        from .models import MissionTransporteur
        from django.utils import timezone
        
        try:
            mission = MissionTransporteur.objects.get(id=self.mission_id)
            mission.statut = new_status
            
            if new_status == 'EN_COURS' and not mission.date_debut:
                mission.date_debut = timezone.now()
            elif new_status == 'TERMINEE':
                mission.date_fin = timezone.now()
                
            mission.save()
            
            # Mettre à jour le statut de la commande
            if new_status == 'EN_COURS':
                mission.commande.statut = 'EN_TRANSIT'
            elif new_status == 'TERMINEE':
                mission.commande.statut = 'LIVREE'
                
            mission.commande.save()
            
        except Exception as e:
            logger.error(f"Erreur update statut: {e}")
    
    @database_sync_to_async
    def create_incident(self, incident_type, description):
        """Créer un incident"""
        from .models import MissionTransporteur, Incident
        
        try:
            mission = MissionTransporteur.objects.get(id=self.mission_id)
            
            Incident.objects.create(
                mission=mission,
                transporteur=mission.transporteur,
                type=incident_type,
                description=description
            )
            
        except Exception as e:
            logger.error(f"Erreur création incident: {e}")


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket pour le tableau de bord temps réel"""
    
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user == AnonymousUser() or not self.user.is_staff:
            await self.close()
            return
        
        self.room_group_name = 'dashboard_updates'
        
        # Rejoindre le groupe
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les stats initiales
        await self.send_dashboard_stats()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Recevoir les demandes de mise à jour"""
        try:
            data = json.loads(text_data)
            
            if data.get('type') == 'refresh_stats':
                await self.send_dashboard_stats()
                
        except Exception as e:
            logger.error(f"Erreur dashboard WS: {e}")
    
    @database_sync_to_async
    def get_dashboard_stats(self):
        """Obtenir les statistiques du tableau de bord"""
        from .models import Commande, Transporteur, MissionTransporteur
        from django.db.models import Count, Q
        from django.utils import timezone
        
        return {
            'commandes_attente': Commande.objects.filter(statut='EN_ATTENTE').count(),
            'transporteurs_disponibles': Transporteur.objects.filter(disponible=True).count(),
            'missions_en_cours': MissionTransporteur.objects.filter(statut='EN_COURS').count(),
            'livraisons_jour': MissionTransporteur.objects.filter(
                date_fin__date=timezone.now().date(),
                statut='TERMINEE'
            ).count()
        }
    
    async def send_dashboard_stats(self):
        """Envoyer les statistiques actualisées"""
        stats = await self.get_dashboard_stats()
        
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'data': stats
        }))
    
    # Méthode pour recevoir les mises à jour du groupe
    async def stats_update(self, event):
        """Recevoir et transmettre les mises à jour de stats"""
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'data': event['data']
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket pour les notifications en temps réel"""
    
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user == AnonymousUser():
            await self.close()
            return
        
        self.user_group_name = f'notifications_{self.user.id}'
        
        # Rejoindre le groupe personnel
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les notifications non lues
        await self.send_unread_notifications()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Gérer les actions sur les notifications"""
        try:
            data = json.loads(text_data)
            
            if data.get('action') == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
            
            elif data.get('action') == 'mark_all_read':
                await self.mark_all_notifications_read()
                
        except Exception as e:
            logger.error(f"Erreur notification WS: {e}")
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """Obtenir les notifications non lues"""
        from .models import Notification
        
        notifications = Notification.objects.filter(
            destinataire=self.user,
            lu=False
        ).order_by('-date_creation')[:20]
        
        return [{
            'id': n.id,
            'type': n.type,
            'titre': n.titre,
            'message': n.message,
            'date': n.date_creation.isoformat(),
            'priorite': n.priorite
        } for n in notifications]
    
    async def send_unread_notifications(self):
        """Envoyer les notifications non lues"""
        notifications = await self.get_unread_notifications()
        
        await self.send(text_data=json.dumps({
            'type': 'unread_notifications',
            'data': notifications
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Marquer une notification comme lue"""
        from .models import Notification
        
        try:
            notification = Notification.objects.get(
                id=notification_id,
                destinataire=self.user
            )
            notification.lu = True
            notification.save()
        except Notification.DoesNotExist:
            pass
    
    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Marquer toutes les notifications comme lues"""
        from .models import Notification
        
        Notification.objects.filter(
            destinataire=self.user,
            lu=False
        ).update(lu=True)
    
    # Méthode pour recevoir les nouvelles notifications
    async def new_notification(self, event):
        """Recevoir et transmettre une nouvelle notification"""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'data': event['notification']
        })):
            logger.error(f"Erreur WebSocket: {e}")
            await self.send_error("Erreur serveur")
    
    async def handle_position_update(self, data):
        """Gérer la mise à jour de position"""
        lat = data.get('lat')
        lon = data.get('lon')
        
        if lat and lon:
            # Mettre à jour la position en base
            await self.update_transporteur_position(lat, lon)
            
            # Diffuser à tous les clients connectés
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'position_broadcast',
                    'lat': lat,
                    'lon': lon,
                    'timestamp': data.get('timestamp'),
                    'speed': data.get('speed'),
                    'heading': data.get('heading')
                }
            )
    
    async def handle_status_update(self, data):
        """Gérer le changement de statut"""
        new_status = data.get('status')
        
        if new_status:
            # Mettre à jour le statut
            await self.update_mission_status(new_status)
            
            # Diffuser le changement
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'status_broadcast',
                    'status': new_status,
                    'timestamp': data.get('timestamp')
                }
            )
    
    async def handle_incident(self, data):
        """Gérer le signalement d'incident"""
        incident_type = data.get('incident_type')
        description = data.get('description')
        
        if incident_type and description:
            # Créer l'incident
            await self.create_incident(incident_type, description)
            
            # Alerter tous les concernés
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'incident_broadcast',
                    'incident_type': incident_type,
                    'description': description,
                    'timestamp': data.get('timestamp')
                }
            )
    
    # Méthodes de diffusion
    async def position_broadcast(self, event):
        """Diffuser une mise à jour de position"""
        await self.send(text_data=json.dumps({
            'type': 'position',
            'data': {
                'lat': event['lat'],
                'lon': event['lon'],
                'timestamp': event['timestamp'],
                'speed': event.get('speed'),
                'heading': event.get('heading')
            }
        }))
    
    async def status_broadcast(self, event):
        """Diffuser un changement de statut"""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': {
                'status': event['status'],
                'timestamp': event['timestamp']
            }
        }))
    
    async def incident_broadcast(self, event):
        """Diffuser un incident"""
        await self.send(text_data=json.dumps({
            'type': 'incident',
            'data': {
                'incident_type': event['incident_type'],
                'description': event['description'],
                'timestamp': event['timestamp']
            }
        }))
    
    async def send_error(self, message):
        """Envoyer un message d'erreur"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    # Méthodes de base de données
    @database_sync_to_async
    def check_permission(self):
        """Vérifier si l'utilisateur a le droit d'accéder à cette mission"""
        from .models import MissionTransporteur
        
        try:
            mission = MissionTransporteur.objects.get(id=self.mission_id)
            user = self.scope["user"]
            
            # Transporteur de la mission
            if hasattr(user, 'transporteur') and mission.transporteur == user.transporteur:
                return True
            
            # Client de la commande
            if hasattr(user, 'client') and mission.commande.client == user.client:
                return True
            
            # Staff
            if user.is_staff:
                return True
                
        except MissionTransporteur.DoesNotExist:
            pass
        
        return False
    
    @database_sync_to_async
    def send_initial_position(self):
        """Envoyer la position initiale"""
        from .models import MissionTransporteur
        
        try:
            mission = MissionTransporteur.objects.get(id=self.mission_id)
            transporteur = mission.transporteur
            
            if transporteur.latitude_actuelle and transporteur.longitude_actuelle:
                return self.send(text_data=json.dumps({
                    'type': 'initial_position',
                    'data': {
                        'lat': transporteur.latitude_actuelle,
                        'lon': transporteur.longitude_actuelle,
                        'last_update': transporteur.derniere_maj_position.isoformat() if transporteur.derniere_maj_position else None
                    }
                }))
        except Exception as e:
            logger.error(f"Erreur position initiale: {e}")
    
    @database_sync_to_async
    def update_transporteur_position(self, lat, lon):
        """Mettre à jour la position du transporteur"""
        from .models import MissionTransporteur
        from django.utils import timezone
        
        try:
            mission = MissionTransporteur.objects.get(id=self.mission_id)
            transporteur = mission.transporteur
            
            transporteur.latitude_actuelle = lat
            transporteur.longitude_actuelle = lon
            transporteur.derniere_maj_position = timezone.now()
            transporteur.save()
            
            # Calculer la distance parcourue
            # ... (implémenter le calcul)
            
        except Exception as e