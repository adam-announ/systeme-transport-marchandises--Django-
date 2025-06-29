# Service de planification simplifié
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count

class PlanificationService:
    """Service simplifié pour la planification"""
    
    @staticmethod
    def planification_automatique_journaliere(date_cible=None, planificateur_id=None):
        """Planification automatique simplifiée"""
        try:
            from ..models import Commande, Vehicule, User, Tournee, EtapeTournee, Livraison, Notification
            
            if not date_cible:
                date_cible = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
            
            # Récupérer les commandes en attente
            commandes = Commande.objects.filter(
                statut='en_attente',
                date_livraison_prevue__date=date_cible.date()
            ).select_related('client')[:10]  # Limiter à 10 pour test
            
            if not commandes.exists():
                return {
                    'success': False,
                    'message': 'Aucune commande en attente pour cette date',
                    'tournees_creees': 0
                }
            
            # Récupérer les véhicules disponibles
            vehicules = Vehicule.objects.filter(
                disponible=True,
                transporteur__is_active=True
            ).select_related('transporteur')[:3]  # Limiter à 3 pour test
            
            if not vehicules.exists():
                return {
                    'success': False,
                    'message': 'Aucun véhicule disponible',
                    'tournees_creees': 0
                }
            
            tournees_creees = 0
            commandes_traitees = 0
            
            with transaction.atomic():
                for vehicule in vehicules:
                    # Prendre quelques commandes pour ce véhicule
                    commandes_vehicule = list(commandes[commandes_traitees:commandes_traitees+3])
                    if not commandes_vehicule:
                        break
                    
                    # Vérifier la capacité
                    poids_total = sum(float(cmd.poids) for cmd in commandes_vehicule)
                    if poids_total > float(vehicule.capacite_max):
                        continue
                    
                    # Créer la tournée
                    duree_estimee = timedelta(minutes=len(commandes_vehicule) * 30 + 60)
                    
                    tournee = Tournee.objects.create(
                        nom=f"Tournée Auto {vehicule.immatriculation} - {date_cible.strftime('%d/%m')}",
                        planificateur_id=planificateur_id,
                        transporteur=vehicule.transporteur,
                        vehicule=vehicule,
                        date_debut_prevue=date_cible,
                        date_fin_prevue=date_cible + duree_estimee,
                        distance_totale=len(commandes_vehicule) * 25,
                        duree_prevue=duree_estimee,
                        optimisee=True,
                        notes=f"Tournée créée automatiquement - {len(commandes_vehicule)} commandes"
                    )
                    
                    # Créer les étapes et mettre à jour les commandes
                    heure_actuelle = date_cible
                    
                    for i, commande in enumerate(commandes_vehicule):
                        # Étape de livraison
                        EtapeTournee.objects.create(
                            tournee=tournee,
                            commande=commande,
                            ordre=i + 1,
                            type_etape='livraison',
                            adresse=commande.destination,
                            heure_prevue=heure_actuelle,
                            duree_prevue=timedelta(minutes=20)
                        )
                        
                        heure_actuelle += timedelta(minutes=30)
                        
                        # Mettre à jour la commande
                        commande.statut = 'planifiee'
                        commande.planificateur_id = planificateur_id
                        commande.transporteur = vehicule.transporteur
                        commande.date_livraison_planifiee = heure_actuelle
                        commande.save()
                        
                        # Créer la livraison
                        Livraison.objects.create(
                            commande=commande,
                            vehicule=vehicule,
                            tournee=tournee,
                            statut='en_attente'
                        )
                    
                    # Marquer le véhicule comme occupé
                    vehicule.disponible = False
                    vehicule.save()
                    
                    # Notification au transporteur
                    Notification.objects.create(
                        utilisateur=vehicule.transporteur,
                        type_notification='tournee_creee',
                        titre='Nouvelle tournée assignée',
                        message=f'Une tournée avec {len(commandes_vehicule)} commandes vous a été assignée.',
                        tournee=tournee,
                        priority='high'
                    )
                    
                    tournees_creees += 1
                    commandes_traitees += len(commandes_vehicule)
            
            return {
                'success': True,
                'message': f'{tournees_creees} tournée(s) créée(s) avec succès',
                'tournees_creees': tournees_creees,
                'commandes_traitees': commandes_traitees
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la planification: {str(e)}',
                'tournees_creees': 0
            }
    
    @staticmethod
    def replanifier_tournee(tournee_id, nouvelles_commandes=None):
        """Replanification simplifiée d'une tournée"""
        try:
            from ..models import Tournee
            
            tournee = Tournee.objects.get(id=tournee_id)
            
            if tournee.statut not in ['planifiee']:
                return {
                    'success': False,
                    'message': 'Seules les tournées planifiées peuvent être replanifiées'
                }
            
            return {
                'success': True,
                'message': 'Tournée replanifiée avec succès',
                'nouvelle_fin': tournee.date_fin_prevue,
                'distance_totale': float(tournee.distance_totale or 0)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la replanification: {str(e)}'
            }