# transport/services.py - Services métier pour séparer la logique

from django.utils import timezone
from django.db.models import Count, Sum, Q, Avg
from django.contrib.auth.models import User
from django.core.cache import cache
from datetime import timedelta
import logging

from .models import (
    Commande, Client, Transporteur, MissionTransporteur, 
    Notification, Adresse, ParametreSysteme
)

logger = logging.getLogger(__name__)

class StatisticsService:
    """Service pour gérer les statistiques"""
    
    @staticmethod
    def get_dashboard_stats(user_type, user=None):
        """Obtenir les statistiques pour le dashboard selon le type d'utilisateur"""
        if user_type in ['admin', 'planificateur']:
            return StatisticsService.get_admin_stats()
        elif user_type == 'client' and user:
            return StatisticsService.get_client_stats(user.client)
        elif user_type == 'transporteur' and user:
            return StatisticsService.get_transporteur_stats(user.transporteur)
        return {}
    
    @staticmethod
    def get_admin_stats():
        """Statistiques pour les administrateurs"""
        cache_key = 'admin_stats'
        stats = cache.get(cache_key)
        
        if not stats:
            today = timezone.now().date()
            
            stats = {
                'commandes_totales': Commande.objects.count(),
                'commandes_attente': Commande.objects.filter(statut='EN_ATTENTE').count(),
                'commandes_en_cours': Commande.objects.filter(
                    statut__in=['AFFECTEE', 'EN_TRANSIT']
                ).count(),
                'commandes_livrees': Commande.objects.filter(statut='LIVREE').count(),
                'transporteurs_total': Transporteur.objects.count(),
                'transporteurs_disponibles': Transporteur.objects.filter(
                    disponible=True, actif=True
                ).count(),
                'missions_en_cours': MissionTransporteur.objects.filter(
                    statut='EN_COURS'
                ).count(),
                'livraisons_jour': MissionTransporteur.objects.filter(
                    statut='TERMINEE',
                    date_fin__date=today
                ).count(),
                'revenus_mois': StatisticsService.calculate_monthly_revenue(),
                'taux_reussite': StatisticsService.calculate_success_rate(),
                'croissance': StatisticsService.calculate_growth_rate(),
            }
            
            # Cache pour 5 minutes
            cache.set(cache_key, stats, 300)
        
        return stats
    
    @staticmethod
    def get_client_stats(client):
        """Statistiques pour un client spécifique"""
        return Commande.objects.filter(client=client).aggregate(
            total=Count('id'),
            livrees=Count('id', filter=Q(statut='LIVREE')),
            en_cours=Count('id', filter=Q(statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT'])),
            annulees=Count('id', filter=Q(statut='ANNULEE')),
            poids_total=Sum('poids'),
            depenses_estimees=Sum('prix_estime'),
        )
    
    @staticmethod
    def get_transporteur_stats(transporteur):
        """Statistiques pour un transporteur spécifique"""
        missions = MissionTransporteur.objects.filter(transporteur=transporteur)
        today = timezone.now().date()
        
        return {
            'missions_totales': missions.count(),
            'missions_terminees': missions.filter(statut='TERMINEE').count(),
            'missions_en_cours': missions.filter(statut__in=['ASSIGNEE', 'EN_COURS']).count(),
            'livraisons_jour': missions.filter(
                statut='TERMINEE',
                date_fin__date=today
            ).count(),
            'note_moyenne': transporteur.note_moyenne,
            'taux_reussite': transporteur.taux_reussite,
            'kilometres_parcourus': missions.aggregate(
                total=Sum('distance_parcourue')
            )['total'] or 0,
        }
    
    @staticmethod
    def calculate_monthly_revenue():
        """Calculer les revenus du mois"""
        try:
            debut_mois = timezone.now().replace(day=1)
            commandes_mois = Commande.objects.filter(
                date_creation__gte=debut_mois,
                statut='LIVREE'
            ).aggregate(
                total=Sum('prix_estime')
            )['total'] or 0
            
            return round(commandes_mois, 2)
        except:
            return 0
    
    @staticmethod
    def calculate_success_rate():
        """Calculer le taux de réussite global"""
        try:
            total_missions = MissionTransporteur.objects.filter(
                statut__in=['TERMINEE', 'ANNULEE']
            ).count()
            
            if total_missions == 0:
                return 100
            
            missions_reussies = MissionTransporteur.objects.filter(
                statut='TERMINEE'
            ).count()
            
            return round((missions_reussies / total_missions) * 100, 1)
        except:
            return 95
    
    @staticmethod
    def calculate_growth_rate():
        """Calculer le taux de croissance mensuel"""
        try:
            today = timezone.now()
            debut_mois = today.replace(day=1)
            debut_mois_precedent = (debut_mois - timedelta(days=1)).replace(day=1)
            
            commandes_mois = Commande.objects.filter(
                date_creation__gte=debut_mois
            ).count()
            
            commandes_mois_precedent = Commande.objects.filter(
                date_creation__gte=debut_mois_precedent,
                date_creation__lt=debut_mois
            ).count()
            
            if commandes_mois_precedent == 0:
                return 100 if commandes_mois > 0 else 0
            
            croissance = ((commandes_mois - commandes_mois_precedent) / commandes_mois_precedent) * 100
            return round(croissance, 1)
        except:
            return 0


class NotificationService:
    """Service pour gérer les notifications"""
    
    @staticmethod
    def create_notification(destinataire, type_notif, titre, message, **kwargs):
        """Créer une notification avec gestion d'erreurs"""
        try:
            notification = Notification.objects.create(
                destinataire=destinataire,
                type=type_notif,
                titre=titre,
                message=message,
                priorite=kwargs.get('priorite', 'NORMALE'),
                commande=kwargs.get('commande'),
                action_url=kwargs.get('action_url', '')
            )
            
            # Log de la création
            logger.info(f"Notification créée: {titre} pour {destinataire.username}")
            
            return notification
        except Exception as e:
            logger.error(f"Erreur création notification: {e}")
            return None
    
    @staticmethod
    def notify_new_order(commande):
        """Notifier les planificateurs d'une nouvelle commande"""
        planificateurs = User.objects.filter(is_staff=True, is_active=True)
        
        for user in planificateurs:
            NotificationService.create_notification(
                destinataire=user,
                type_notif='MISSION',
                titre='Nouvelle commande à affecter',
                message=f'Commande #{commande.id} - {commande.type_marchandise} '
                       f'({commande.poids}kg) - {commande.adresse_enlevement.ville} → '
                       f'{commande.adresse_livraison.ville}',
                commande=commande,
                priorite='HAUTE' if commande.priorite == 2 else 'NORMALE',
                action_url=f'/planificateur/commande/{commande.id}/affecter/'
            )
    
    @staticmethod
    def notify_status_change(mission, nouveau_statut, commentaire=''):
        """Notifier le changement de statut d'une mission"""
        # Notifier le client
        NotificationService.create_notification(
            destinataire=mission.commande.client.user,
            type_notif='STATUT',
            titre=f"Mise à jour de votre commande #{mission.commande.id}",
            message=f"Nouveau statut: {mission.get_statut_display()}. {commentaire}",
            commande=mission.commande,
            action_url=f'/commande/{mission.commande.id}/suivre/'
        )
        
        # Notifier les administrateurs si c'est important
        if nouveau_statut in ['ANNULEE'] or mission.commande.priorite == 2:
            admins = User.objects.filter(is_staff=True, is_active=True)
            for admin in admins:
                NotificationService.create_notification(
                    destinataire=admin,
                    type_notif='STATUT',
                    titre=f"Changement de statut - Commande #{mission.commande.id}",
                    message=f"Mission passée en {mission.get_statut_display()}",
                    commande=mission.commande,
                    priorite='HAUTE'
                )
    
    @staticmethod
    def notify_incident(incident):
        """Notifier un incident"""
        # Notifier les administrateurs
        admins = User.objects.filter(is_staff=True, is_active=True)
        for admin in admins:
            NotificationService.create_notification(
                destinataire=admin,
                type_notif='INCIDENT',
                titre=f"Incident sur commande #{incident.mission.commande.id}",
                message=f"Type: {incident.get_type_display()} - {incident.description[:100]}",
                commande=incident.mission.commande,
                priorite='HAUTE'
            )
        
        # Notifier le client
        NotificationService.create_notification(
            destinataire=incident.mission.commande.client.user,
            type_notif='INCIDENT',
            titre="Incident sur votre livraison",
            message=f"Un incident a été signalé: {incident.get_type_display()}",
            commande=incident.mission.commande
        )
    
    @staticmethod
    def get_user_notifications(user, limit=10, unread_only=False):
        """Obtenir les notifications d'un utilisateur"""
        queryset = Notification.objects.filter(destinataire=user)
        
        if unread_only:
            queryset = queryset.filter(lu=False)
        
        return queryset.select_related('commande').order_by('-date_creation')[:limit]


class PricingService:
    """Service pour gérer les calculs de prix"""
    
    @staticmethod
    def calculate_price(poids, distance, type_marchandise, priorite=0):
        """Calculer le prix d'une commande"""
        try:
            # Paramètres de base
            prix_base = PricingService.get_parameter('prix_base_livraison', 50)
            prix_kg = PricingService.get_parameter('prix_par_kg', 2)
            prix_km = PricingService.get_parameter('prix_par_km', 1.5)
            
            # Multiplicateurs selon le type
            multiplicateurs = {
                'standard': 1.0,
                'fragile': 1.3,
                'perissable': 1.5,
                'dangereux': 2.0,
                'urgent': 1.8,
            }
            
            # Multiplicateur de priorité
            multiplicateur_priorite = {
                0: 1.0,  # Normale
                1: 1.2,  # Haute
                2: 1.5,  # Urgente
            }
            
            # Calcul de base
            prix_total = prix_base + (poids * prix_kg) + (distance * prix_km)
            
            # Application des multiplicateurs
            mult_type = multiplicateurs.get(type_marchandise.lower(), 1.0)
            mult_prio = multiplicateur_priorite.get(priorite, 1.0)
            
            prix_total *= mult_type * mult_prio
            
            # Remises selon le volume
            if poids > 1000:  # Plus de 1 tonne
                prix_total *= 0.95  # 5% de remise
            elif poids > 500:  # Plus de 500kg
                prix_total *= 0.97  # 3% de remise
            
            return round(prix_total, 2)
            
        except Exception as e:
            logger.error(f"Erreur calcul prix: {e}")
            return 100.0
    
    @staticmethod
    def get_parameter(nom, default_value):
        """Récupérer un paramètre système"""
        try:
            param = ParametreSysteme.objects.get(nom=nom)
            return float(param.valeur) if param.type in ['FLOAT', 'INTEGER'] else param.valeur
        except (ParametreSysteme.DoesNotExist, ValueError):
            return default_value
    
    @staticmethod
    def estimate_delivery_time(distance, conditions_meteo=None, conditions_trafic=None):
        """Estimer le temps de livraison"""
        # Vitesse de base
        vitesse_base = 60  # km/h
        
        # Ajustements selon les conditions
        if conditions_meteo:
            if conditions_meteo in ['pluie', 'neige']:
                vitesse_base *= 0.8
            elif conditions_meteo == 'brouillard':
                vitesse_base *= 0.6
        
        if conditions_trafic:
            if conditions_trafic == 'dense':
                vitesse_base *= 0.7
            elif conditions_trafic == 'bloque':
                vitesse_base *= 0.5
        
        # Temps en heures
        temps_heures = distance / vitesse_base
        
        # Ajout du temps de chargement/déchargement
        temps_heures += 0.5
        
        return round(temps_heures, 1)


class AddressService:
    """Service pour gérer les adresses"""
    
    @staticmethod
    def get_client_frequent_addresses(client, limit=5):
        """Obtenir les adresses fréquemment utilisées par un client"""
        # Adresses d'enlèvement
        enlevements = Adresse.objects.filter(
            commandes_enlevement__client=client
        ).annotate(
            usage_count=Count('commandes_enlevement')
        ).order_by('-usage_count', '-id')[:limit]
        
        # Adresses de livraison
        livraisons = Adresse.objects.filter(
            commandes_livraison__client=client
        ).annotate(
            usage_count=Count('commandes_livraison')
        ).order_by('-usage_count', '-id')[:limit]
        
        return {
            'enlevements': enlevements,
            'livraisons': livraisons
        }
    
    @staticmethod
    def calculate_distance(addr1, addr2):
        """Calculer la distance entre deux adresses"""
        try:
            from .utils import calculer_distance
            
            if all([addr1.latitude, addr1.longitude, addr2.latitude, addr2.longitude]):
                return calculer_distance(
                    addr1.latitude, addr1.longitude,
                    addr2.latitude, addr2.longitude
                )
            else:
                return AddressService.estimate_distance_by_cities(addr1.ville, addr2.ville)
        except:
            return 50
    
    @staticmethod
    def estimate_distance_by_cities(ville1, ville2):
        """Estimer la distance entre villes"""
        # Matrice des distances entre principales villes du Maroc
        distances = {
            ('Casablanca', 'Rabat'): 90,
            ('Casablanca', 'Marrakech'): 240,
            ('Casablanca', 'Fès'): 300,
            ('Casablanca', 'Tanger'): 340,
            ('Casablanca', 'Agadir'): 500,
            ('Rabat', 'Fès'): 200,
            ('Rabat', 'Marrakech'): 320,
            ('Rabat', 'Tanger'): 250,
            ('Marrakech', 'Agadir'): 260,
            ('Marrakech', 'Fès'): 480,
            ('Fès', 'Tanger'): 200,
            ('Fès', 'Oujda'): 160,
            ('Tanger', 'Tétouan'): 60,
        }
        
        # Chercher dans les deux sens
        distance = distances.get((ville1, ville2)) or distances.get((ville2, ville1))
        
        if distance:
            return distance
        
        # Si pas trouvé, estimation par défaut
        return 150


class ReportService:
    """Service pour générer des rapports"""
    
    @staticmethod
    def generate_client_report(client, date_debut, date_fin):
        """Générer un rapport pour un client"""
        commandes = Commande.objects.filter(
            client=client,
            date_creation__date__gte=date_debut,
            date_creation__date__lte=date_fin
        ).select_related('transporteur', 'adresse_enlevement', 'adresse_livraison')
        
        stats = commandes.aggregate(
            total=Count('id'),
            livrees=Count('id', filter=Q(statut='LIVREE')),
            en_cours=Count('id', filter=Q(statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT'])),
            annulees=Count('id', filter=Q(statut='ANNULEE')),
            poids_total=Sum('poids'),
            prix_total=Sum('prix_estime')
        )
        
        # Calculs supplémentaires
        taux_livraison = 0
        if stats['total'] > 0:
            taux_livraison = round((stats['livrees'] / stats['total']) * 100, 1)
        
        return {
            'commandes': commandes,
            'stats': stats,
            'taux_livraison': taux_livraison,
            'periode': f"{date_debut.strftime('%d/%m/%Y')} - {date_fin.strftime('%d/%m/%Y')}"
        }
    
    @staticmethod
    def generate_admin_report(date_debut, date_fin):
        """Générer un rapport global pour les administrateurs"""
        commandes = Commande.objects.filter(
            date_creation__date__gte=date_debut,
            date_creation__date__lte=date_fin
        ).select_related('client', 'transporteur')
        
        # Statistiques globales
        stats = commandes.aggregate(
            total=Count('id'),
            livrees=Count('id', filter=Q(statut='LIVREE')),
            en_cours=Count('id', filter=Q(statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT'])),
            annulees=Count('id', filter=Q(statut='ANNULEE')),
            revenus=Sum('prix_estime', filter=Q(statut='LIVREE'))
        )
        
        # Top clients
        top_clients = Client.objects.filter(
            commande__date_creation__date__gte=date_debut,
            commande__date_creation__date__lte=date_fin
        ).annotate(
            nb_commandes=Count('commande'),
            chiffre_affaires=Sum('commande__prix_estime', filter=Q(commande__statut='LIVREE'))
        ).order_by('-nb_commandes')[:10]
        
        # Top transporteurs
        top_transporteurs = Transporteur.objects.filter(
            missiontransporteur__date_assignation__date__gte=date_debut,
            missiontransporteur__date_assignation__date__lte=date_fin
        ).annotate(
            nb_missions=Count('missiontransporteur'),
            nb_livrees=Count('missiontransporteur', filter=Q(missiontransporteur__statut='TERMINEE'))
        ).order_by('-nb_missions')[:10]
        
        return {
            'commandes': commandes,
            'stats': stats,
            'top_clients': top_clients,
            'top_transporteurs': top_transporteurs,
            'periode': f"{date_debut.strftime('%d/%m/%Y')} - {date_fin.strftime('%d/%m/%Y')}"
        }