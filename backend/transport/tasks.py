# transport/tasks.py
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import requests
import logging
from .models import *
from .utils import envoyer_notification

logger = logging.getLogger(__name__)

@shared_task
def update_traffic_data():
    """Mettre à jour les données de trafic"""
    try:
        # Simuler la récupération de données de trafic
        # En production, vous utiliseriez une vraie API comme TomTom ou Google Maps
        
        # Exemples de localisation au Maroc
        locations = [
            {"name": "Casablanca Centre", "lat": 33.5731, "lng": -7.5898},
            {"name": "Rabat Centre", "lat": 34.0209, "lng": -6.8416},
            {"name": "Marrakech Centre", "lat": 31.6295, "lng": -7.9811},
        ]
        
        for location in locations:
            # Simuler des données de trafic aléatoires
            import random
            
            intensite = random.choice(['faible', 'moyenne', 'elevee'])
            type_incident = random.choice(['embouteillage', 'accident', 'travaux', 'aucun'])
            
            DonneesTrafic.objects.create(
                localisation=location["name"],
                latitude=location["lat"],
                longitude=location["lng"],
                intensite=intensite,
                type_incident=type_incident,
                description=f"Trafic {intensite} détecté"
            )
        
        # Nettoyer les anciennes données (garder seulement 24h)
        cutoff = timezone.now() - timedelta(hours=24)
        DonneesTrafic.objects.filter(timestamp__lt=cutoff).delete()
        
        logger.info("Données de trafic mises à jour avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du trafic: {e}")

@shared_task
def update_weather_data():
    """Mettre à jour les données météo"""
    try:
        weather_api_key = getattr(settings, 'WEATHER_API_KEY', None)
        
        if not weather_api_key:
            logger.warning("Clé API météo non configurée")
            return
        
        # Villes principales du Maroc
        cities = [
            {"name": "Casablanca", "lat": 33.5731, "lng": -7.5898},
            {"name": "Rabat", "lat": 34.0209, "lng": -6.8416},
            {"name": "Marrakech", "lat": 31.6295, "lng": -7.9811},
            {"name": "Fès", "lat": 34.0331, "lng": -5.0003},
            {"name": "Tanger", "lat": 35.7595, "lng": -5.8340},
        ]
        
        for city in cities:
            try:
                # Appel à l'API OpenWeatherMap
                url = f"https://api.openweathermap.org/data/2.5/weather"
                params = {
                    'lat': city['lat'],
                    'lon': city['lng'],
                    'appid': weather_api_key,
                    'units': 'metric',
                    'lang': 'fr'
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                DonneesMeteo.objects.create(
                    localisation=city['name'],
                    latitude=city['lat'],
                    longitude=city['lng'],
                    temperature=data['main']['temp'],
                    conditions_meteo=data['weather'][0]['description'],
                    humidite=data['main']['humidity'],
                    vitesse_vent=data['wind'].get('speed', 0),
                    visibilite=data.get('visibility', 10000) / 1000  # Convertir en km
                )
                
            except requests.RequestException as e:
                logger.error(f"Erreur API météo pour {city['name']}: {e}")
            except Exception as e:
                logger.error(f"Erreur traitement météo pour {city['name']}: {e}")
        
        # Nettoyer les anciennes données (garder 48h)
        cutoff = timezone.now() - timedelta(hours=48)
        DonneesMeteo.objects.filter(timestamp__lt=cutoff).delete()
        
        logger.info("Données météo mises à jour avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour météo: {e}")

@shared_task
def cleanup_old_notifications():
    """Nettoyer les anciennes notifications"""
    try:
        # Supprimer les notifications lues de plus de 30 jours
        cutoff_read = timezone.now() - timedelta(days=30)
        deleted_read = Notification.objects.filter(
            lue=True,
            date_creation__lt=cutoff_read
        ).delete()
        
        # Supprimer les notifications non lues de plus de 90 jours
        cutoff_unread = timezone.now() - timedelta(days=90)
        deleted_unread = Notification.objects.filter(
            lue=False,
            date_creation__lt=cutoff_unread
        ).delete()
        
        logger.info(f"Notifications nettoyées: {deleted_read[0]} lues, {deleted_unread[0]} non lues")
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des notifications: {e}")

@shared_task
def check_commande_delays():
    """Vérifier les retards dans les commandes"""
    try:
        now = timezone.now()
        
        # Commandes en retard pour l'enlèvement
        commandes_retard_enlevement = Commande.objects.filter(
            statut='assignee',
            date_enlevement_prevue__lt=now
        )
        
        for commande in commandes_retard_enlevement:
            # Notifier le client
            envoyer_notification(
                destinataire=commande.client.utilisateur.user,
                type_notification='incident',
                titre='Retard d\'enlèvement',
                message=f'L\'enlèvement de votre commande {commande.numero} est en retard.',
                commande=commande
            )
            
            # Notifier le transporteur
            if commande.transporteur:
                envoyer_notification(
                    destinataire=commande.transporteur.utilisateur.user,
                    type_notification='incident',
                    titre='Enlèvement en retard',
                    message=f'L\'enlèvement de la commande {commande.numero} est en retard.',
                    commande=commande
                )
        
        # Commandes en retard pour la livraison
        commandes_retard_livraison = Commande.objects.filter(
            statut__in=['en_transit', 'en_cours_livraison'],
            date_livraison_prevue__lt=now
        )
        
        for commande in commandes_retard_livraison:
            # Notifier le client
            envoyer_notification(
                destinataire=commande.client.utilisateur.user,
                type_notification='incident',
                titre='Retard de livraison',
                message=f'La livraison de votre commande {commande.numero} est en retard.',
                commande=commande
            )
        
        logger.info(f"Vérification des retards: {len(commandes_retard_enlevement)} enlèvements, {len(commandes_retard_livraison)} livraisons")
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des retards: {e}")

@shared_task
def auto_assign_commandes():
    """Assignation automatique des commandes en attente"""
    try:
        from .utils import trouver_transporteur_optimal
        
        commandes_en_attente = Commande.objects.filter(
            statut='en_attente',
            transporteur__isnull=True
        ).order_by('date_creation')
        
        assigned_count = 0
        
        for commande in commandes_en_attente:
            transporteur = trouver_transporteur_optimal(commande)
            
            if transporteur:
                commande.transporteur = transporteur
                commande.statut = 'assignee'
                commande.save()
                
                # Créer le tracking
                Tracking.objects.create(
                    commande=commande,
                    etape='transporteur_assigne',
                    description=f'Transporteur {transporteur.utilisateur.full_name} assigné automatiquement'
                )
                
                # Notifications
                envoyer_notification(
                    destinataire=transporteur.utilisateur.user,
                    type_notification='assignation',
                    titre='Nouvelle mission assignée',
                    message=f'La commande {commande.numero} vous a été assignée automatiquement.',
                    commande=commande
                )
                
                envoyer_notification(
                    destinataire=commande.client.utilisateur.user,
                    type_notification='assignation',
                    titre='Transporteur assigné',
                    message=f'Un transporteur a été assigné à votre commande {commande.numero}.',
                    commande=commande
                )
                
                assigned_count += 1
        
        logger.info(f"Assignation automatique: {assigned_count} commandes assignées")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'assignation automatique: {e}")

@shared_task
def generate_daily_reports():
    """Générer les rapports quotidiens"""
    try:
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Statistiques du jour précédent
        stats = {
            'commandes_creees': Commande.objects.filter(date_creation__date=yesterday).count(),
            'commandes_livrees': Commande.objects.filter(
                statut='livree',
                date_livraison_effective__date=yesterday
            ).count(),
            'incidents': Incident.objects.filter(date_creation__date=yesterday).count(),
            'nouveaux_clients': Client.objects.filter(
                utilisateur__user__date_joined__date=yesterday
            ).count(),
        }
        
        # Notifier les administrateurs
        admins = User.objects.filter(
            utilisateur__role='admin',
            is_active=True
        )
        
        message = f"""Rapport quotidien du {yesterday.strftime('%d/%m/%Y')}:
- Nouvelles commandes: {stats['commandes_creees']}
- Commandes livrées: {stats['commandes_livrees']}
- Incidents: {stats['incidents']}
- Nouveaux clients: {stats['nouveaux_clients']}"""
        
        for admin in admins:
            envoyer_notification(
                destinataire=admin,
                type_notification='systeme',
                titre='Rapport quotidien TransportPro',
                message=message
            )
        
        logger.info(f"Rapport quotidien généré: {stats}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport: {e}")

@shared_task
def backup_database():
    """Tâche de sauvegarde de base de données (simulation)"""
    try:
        # En production, vous ajouteriez ici la logique de sauvegarde
        # Par exemple, dump de la base de données, upload vers un stockage cloud, etc.
        
        backup_time = timezone.now()
        logger.info(f"Sauvegarde de base de données simulée à {backup_time}")
        
        # Notifier les administrateurs
        admins = User.objects.filter(
            utilisateur__role='admin',
            is_active=True
        )
        
        for admin in admins:
            envoyer_notification(
                destinataire=admin,
                type_notification='systeme',
                titre='Sauvegarde effectuée',
                message=f'Sauvegarde automatique effectuée le {backup_time.strftime("%d/%m/%Y à %H:%M")}'
            )
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde: {e}")

@shared_task
def send_weekly_reports():
    """Envoyer les rapports hebdomadaires"""
    try:
        from datetime import datetime
        
        # Calculer la semaine précédente
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday() + 7)  # Lundi de la semaine dernière
        week_end = week_start + timedelta(days=6)  # Dimanche de la semaine dernière
        
        # Statistiques de la semaine
        stats = {
            'commandes': Commande.objects.filter(
                date_creation__date__range=[week_start, week_end]
            ).count(),
            'chiffre_affaires': Commande.objects.filter(
                date_creation__date__range=[week_start, week_end],
                prix_final__isnull=False
            ).aggregate(total=models.Sum('prix_final'))['total'] or 0,
            'taux_livraison': 0
        }
        
        total_commandes = Commande.objects.filter(
            date_creation__date__range=[week_start, week_end]
        ).count()
        
        if total_commandes > 0:
            commandes_livrees = Commande.objects.filter(
                date_creation__date__range=[week_start, week_end],
                statut='livree'
            ).count()
            stats['taux_livraison'] = round((commandes_livrees / total_commandes) * 100, 1)
        
        # Envoyer aux clients et transporteurs
        clients = Client.objects.filter(utilisateur__user__is_active=True)
        transporteurs = Transporteur.objects.filter(utilisateur__user__is_active=True)
        
        for client in clients:
            commandes_client = Commande.objects.filter(
                client=client,
                date_creation__date__range=[week_start, week_end]
            ).count()
            
            if commandes_client > 0:
                message = f"""Rapport hebdomadaire ({week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}):
Vous avez effectué {commandes_client} commande(s) cette semaine."""
                
                envoyer_notification(
                    destinataire=client.utilisateur.user,
                    type_notification='systeme',
                    titre='Rapport hebdomadaire',
                    message=message
                )
        
        logger.info(f"Rapports hebdomadaires envoyés pour la semaine {week_start} - {week_end}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi des rapports hebdomadaires: {e}")