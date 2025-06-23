# transport/services.py - Services métier optimisés

from django.utils import timezone
from django.db.models import Count, Sum, Q, Avg
from django.contrib.auth.models import User
from django.core.cache import cache
from datetime import timedelta
import logging

from .models import (
    Commande, Client, Transporteur, MissionTransporteur, 
    Notification, ParametreSysteme
)

logger = logging.getLogger(__name__)

class StatisticsService:
    """Service pour gérer les statistiques"""
    
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
                'taux_reussite': StatisticsService.calculate_success_rate(),
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
        }
    
    @staticmethod
    def get_public_stats():
        """Statistiques publiques pour la page d'accueil"""
        cache_key = 'public_stats'
        stats = cache.get(cache_key)
        
        if not stats:
            stats = {
                'total_livraisons': Commande.objects.filter(statut='LIVREE').count(),
                'clients_actifs': Client.objects.filter(actif=True).count(),
                'transporteurs_actifs': Transporteur.objects.filter(
                    disponible=True, actif=True
                ).count(),
                'villes_couvertes': StatisticsService.get_covered_cities_count(),
            }
            # Cache pour 1 heure
            cache.set(cache_key, stats, 3600)
        
        return stats
    
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
    def get_covered_cities_count():
        """Calculer le nombre de villes couvertes"""
        try:
            from .models import Adresse
            
            villes_enlevement = set(Adresse.objects.filter(
                commandes_enlevement__isnull=False
            ).values_list('ville', flat=True))
            
            villes_livraison = set(Adresse.objects.filter(
                commandes_livraison__isnull=False
            ).values_list('ville', flat=True))
            
            return len(villes_enlevement.union(villes_livraison))
        except:
            return 15

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
            )
            
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
        )
        
        # Notifier les administrateurs si important
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

class AddressService:
    """Service pour gérer les adresses"""
    
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
        distances = {
            ('Casablanca', 'Rabat'): 90,
            ('Casablanca', 'Marrakech'): 240,
            ('Rabat', 'Fès'): 200,
            ('Casablanca', 'Fès'): 290,
            ('Marrakech', 'Agadir'): 250,
            ('Casablanca', 'Tanger'): 340,
        }
        
        key1 = (ville1, ville2)
        key2 = (ville2, ville1)
        
        return distances.get(key1, distances.get(key2, 100))

class ValidationService:
    """Service pour les validations métier"""
    
    @staticmethod
    def can_assign_transporteur(transporteur, commande):
        """Vérifier si un transporteur peut être assigné"""
        if not transporteur.disponible:
            return False, "Transporteur non disponible"
        
        if transporteur.capacite_charge < commande.poids:
            return False, "Capacité insuffisante"
        
        # Vérifier les missions en cours
        missions_actives = transporteur.missiontransporteur_set.filter(
            statut__in=['ASSIGNEE', 'EN_COURS']
        ).count()
        
        if missions_actives >= 3:  # Limite configurable
            return False, "Trop de missions en cours"
        
        return True, "Assignation possible"
    
    @staticmethod
    def can_cancel_order(commande, user):
        """Vérifier si une commande peut être annulée"""
        # Vérifier les permissions
        if not (user.is_staff or (hasattr(user, 'client') and commande.client == user.client)):
            return False, "Permissions insuffisantes"
        
        # Vérifier le statut
        if commande.statut in ['EN_TRANSIT', 'LIVREE']:
            return False, "Commande en cours ou livrée"
        
        # Vérifier le délai (24h par défaut)
        delai_h = 24
        try:
            param = ParametreSysteme.objects.get(nom='delai_annulation')
            delai_h = int(param.valeur)
        except:
            pass
        
        limite = commande.date_creation + timedelta(hours=delai_h)
        if timezone.now() > limite:
            return False, f"Délai dépassé ({delai_h}h)"
        
        return True, "Annulation autorisée"

class ReportService:
    """Service pour générer des rapports"""
    
    @staticmethod
    def generate_client_report(client, date_debut, date_fin):
        """Générer un rapport pour un client"""
        commandes = Commande.objects.filter(
            client=client,
            date_creation__date__gte=date_debut,
            date_creation__date__lte=date_fin
        ).select_related('transporteur')
        
        stats = commandes.aggregate(
            total=Count('id'),
            livrees=Count('id', filter=Q(statut='LIVREE')),
            en_cours=Count('id', filter=Q(statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT'])),
            annulees=Count('id', filter=Q(statut='ANNULEE')),
            poids_total=Sum('poids')
        )
        
        # Calcul du taux de livraison
        taux_livraison = 0
        if stats['total'] > 0:
            taux_livraison = round((stats['livrees'] / stats['total']) * 100, 1)
        
        return {
            'commandes': commandes,
            'stats': stats,
            'taux_livraison': taux_livraison,
            'periode': f"{date_debut.strftime('%d/%m/%Y')} - {date_fin.strftime('%d/%m/%Y')}"
        }

class OptimizationService:
    """Service pour l'optimisation des itinéraires et affectations"""
    
    @staticmethod
    def suggest_best_transporteurs(commande):
        """Suggérer les meilleurs transporteurs pour une commande"""
        transporteurs = Transporteur.objects.filter(
            disponible=True,
            actif=True,
            capacite_charge__gte=commande.poids
        ).select_related('user')
        
        suggestions = []
        for transporteur in transporteurs:
            score = OptimizationService.calculate_transporteur_score(transporteur, commande)
            if score > 0:
                suggestions.append({
                    'transporteur': transporteur,
                    'score': score,
                    'missions_actives': transporteur.missiontransporteur_set.filter(
                        statut__in=['ASSIGNEE', 'EN_COURS']
                    ).count(),
                    'taux_reussite': transporteur.taux_reussite
                })
        
        # Trier par score décroissant
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:5]
    
    @staticmethod
    def calculate_transporteur_score(transporteur, commande):
        """Calculer un score d'adéquation transporteur/commande"""
        score = 100
        
        # Capacité de charge
        if transporteur.capacite_charge < commande.poids:
            return 0
        elif transporteur.capacite_charge < commande.poids * 1.5:
            score -= 10
        
        # Missions en cours
        missions_actives = transporteur.missiontransporteur_set.filter(
            statut__in=['ASSIGNEE', 'EN_COURS']
        ).count()
        score -= missions_actives * 15
        
        # Note moyenne
        if transporteur.note_moyenne < 3:
            score -= 30
        elif transporteur.note_moyenne > 4.5:
            score += 10
        
        # Priorité de la commande
        if commande.priorite == 2 and missions_actives == 0:
            score += 20
        
        return max(0, score)

class MonitoringService:
    """Service pour le monitoring et les alertes"""
    
    @staticmethod
    def check_system_health():
        """Vérifier la santé du système"""
        issues = []
        
        # Commandes en attente depuis trop longtemps
        commandes_anciennes = Commande.objects.filter(
            statut='EN_ATTENTE',
            date_creation__lt=timezone.now() - timedelta(hours=24)
        ).count()
        
        if commandes_anciennes > 0:
            issues.append({
                'type': 'warning',
                'message': f'{commandes_anciennes} commandes en attente depuis +24h',
                'action': 'Vérifier les affectations'
            })
        
        # Transporteurs inactifs
        transporteurs_inactifs = Transporteur.objects.filter(
            derniere_maj_position__lt=timezone.now() - timedelta(hours=6),
            disponible=True
        ).count()
        
        if transporteurs_inactifs > 0:
            issues.append({
                'type': 'info',
                'message': f'{transporteurs_inactifs} transporteurs sans mise à jour position',
                'action': 'Contacter les transporteurs'
            })
        
        # Incidents non résolus
        incidents_ouverts = Incident.objects.filter(
            resolu=False,
            date_signalement__lt=timezone.now() - timedelta(hours=12)
        ).count()
        
        if incidents_ouverts > 0:
            issues.append({
                'type': 'error',
                'message': f'{incidents_ouverts} incidents non résolus',
                'action': 'Traiter les incidents'
            })
        
        return issues
    
    @staticmethod
    def get_performance_metrics():
        """Obtenir les métriques de performance"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # Temps moyen de traitement des commandes
        from django.db.models import Avg, F
        
        temps_moyen = MissionTransporteur.objects.filter(
            statut='TERMINEE',
            date_fin__date__gte=week_ago
        ).aggregate(
            temps_moyen=Avg(F('date_fin') - F('date_assignation'))
        )['temps_moyen']
        
        # Taux de livraison dans les délais
        missions_semaine = MissionTransporteur.objects.filter(
            date_assignation__date__gte=week_ago
        )
        
        total_missions = missions_semaine.count()
        missions_a_temps = missions_semaine.filter(
            statut='TERMINEE',
            date_fin__lte=F('date_assignation') + timedelta(days=2)
        ).count()
        
        taux_ponctualite = 0
        if total_missions > 0:
            taux_ponctualite = round((missions_a_temps / total_missions) * 100, 1)
        
        return {
            'temps_moyen_heures': temps_moyen.total_seconds() / 3600 if temps_moyen else 0,
            'taux_ponctualite': taux_ponctualite,
            'missions_semaine': total_missions,
            'periode': f"{week_ago.strftime('%d/%m')} - {today.strftime('%d/%m')}"
        }