# API spécialisée pour le planificateur avec données réelles
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from datetime import datetime, timedelta
import json

from .models import (
    User, Commande, Vehicule, Tournee, EtapeTournee, 
    Livraison, Notification
)
try:
    from .services.planification_service import PlanificationService
except ImportError:
    from .services.planification_service_simple import PlanificationService

def planificateur_required_api(view_func):
    """Décorateur pour vérifier que l'utilisateur est un planificateur"""
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'planificateur':
            return JsonResponse({'success': False, 'message': 'Accès non autorisé'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@planificateur_required_api
@require_http_methods(["POST"])
def planification_automatique_api(request):
    """API pour la planification automatique des commandes"""
    try:
        data = json.loads(request.body)
        user_id = request.session['user_id']
        
        # Paramètres de planification
        date_planification = data.get('date_planification')
        heure_debut = data.get('heure_debut', '08:00')
        priorite_min = data.get('priorite_min', 'basse')
        zone = data.get('zone', 'toutes')
        optimiser = data.get('optimiser', True)
        verifier_meteo = data.get('verifier_meteo', False)
        
        # Construire la date/heure de début
        if date_planification:
            date_debut = datetime.strptime(f"{date_planification} {heure_debut}", "%Y-%m-%d %H:%M")
            date_debut = timezone.make_aware(date_debut)
        else:
            date_debut = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        # Filtrer les commandes selon les critères
        commandes_query = Commande.objects.filter(statut='en_attente')
        
        # Filtre par priorité
        if priorite_min != 'basse':
            priorites_map = {
                'normale': ['normale', 'haute', 'urgente'],
                'haute': ['haute', 'urgente'],
                'urgente': ['urgente']
            }
            commandes_query = commandes_query.filter(priorite__in=priorites_map[priorite_min])
        
        # Filtre par zone géographique
        if zone != 'toutes':
            commandes_query = commandes_query.filter(
                Q(origine__icontains=zone) | Q(destination__icontains=zone)
            )
        
        # Filtre par date de livraison (même jour)
        commandes_query = commandes_query.filter(
            date_livraison_prevue__date=date_debut.date()
        )
        
        commandes = list(commandes_query.select_related('client'))
        
        if not commandes:
            return JsonResponse({
                'success': False,
                'message': 'Aucune commande trouvée avec ces critères'
            })
        
        # Lancer la planification automatique
        resultat = PlanificationService.planification_automatique_journaliere(
            date_cible=date_debut,
            planificateur_id=user_id
        )
        
        return JsonResponse(resultat)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la planification: {str(e)}'
        })

@planificateur_required_api
@require_http_methods(["POST"])
def planification_rapide_api(request):
    """API pour la planification rapide de commandes sélectionnées"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else {}
        user_id = request.session['user_id']
        
        # Récupérer les IDs des commandes depuis le formulaire ou JSON
        if request.content_type == 'application/json':
            commandes_ids = data.get('commandes', [])
        else:
            commandes_str = request.POST.get('commandes', '[]')
            commandes_ids = json.loads(commandes_str)
        
        if not commandes_ids:
            return JsonResponse({
                'success': False,
                'message': 'Aucune commande sélectionnée'
            })
        
        # Paramètres de planification
        date_planification = request.POST.get('date_planification') or data.get('date_planification')
        heure_debut = request.POST.get('heure_debut', '08:00') or data.get('heure_debut', '08:00')
        strategie = request.POST.get('strategie', 'automatique') or data.get('strategie', 'automatique')
        optimiser = request.POST.get('optimiser') == 'on' or data.get('optimiser', True)
        grouper = request.POST.get('grouper') == 'on' or data.get('grouper', True)
        
        # Construire la date/heure
        date_debut = datetime.strptime(f"{date_planification} {heure_debut}", "%Y-%m-%d %H:%M")
        date_debut = timezone.make_aware(date_debut)
        
        # Récupérer les commandes
        commandes = Commande.objects.filter(
            id__in=commandes_ids,
            statut='en_attente'
        ).select_related('client')
        
        if not commandes.exists():
            return JsonResponse({
                'success': False,
                'message': 'Aucune commande valide trouvée'
            })
        
        # Appliquer la stratégie de planification
        if strategie == 'proximite' and grouper:
            # Grouper par zones géographiques
            zones_commandes = PlanificationService.grouper_par_zones(list(commandes))
            tournees_creees = []
            
            for zone, commandes_zone in zones_commandes.items():
                if len(commandes_zone) >= 2:
                    # Créer une tournée pour cette zone
                    resultat_zone = PlanificationService.planification_automatique_journaliere(
                        date_cible=date_debut,
                        planificateur_id=user_id
                    )
                    if resultat_zone['success']:
                        tournees_creees.extend(resultat_zone.get('tournees', []))
            
            return JsonResponse({
                'success': True,
                'message': f'{len(tournees_creees)} tournée(s) créée(s) par zone géographique',
                'tournees_creees': len(tournees_creees),
                'strategie': 'proximite'
            })
        
        elif strategie == 'priorite':
            # Trier par priorité et créer des tournées
            commandes_urgentes = [cmd for cmd in commandes if cmd.priorite == 'urgente']
            commandes_autres = [cmd for cmd in commandes if cmd.priorite != 'urgente']
            
            tournees_creees = 0
            
            # Traiter d'abord les urgentes
            if commandes_urgentes:
                resultat_urgentes = PlanificationService.planification_automatique_journaliere(
                    date_cible=date_debut,
                    planificateur_id=user_id
                )
                if resultat_urgentes['success']:
                    tournees_creees += resultat_urgentes['tournees_creees']
            
            # Puis les autres
            if commandes_autres:
                resultat_autres = PlanificationService.planification_automatique_journaliere(
                    date_cible=date_debut + timedelta(hours=1),
                    planificateur_id=user_id
                )
                if resultat_autres['success']:
                    tournees_creees += resultat_autres['tournees_creees']
            
            return JsonResponse({
                'success': True,
                'message': f'{tournees_creees} tournée(s) créée(s) par priorité',
                'tournees_creees': tournees_creees,
                'strategie': 'priorite'
            })
        
        else:
            # Planification automatique standard
            resultat = PlanificationService.planification_automatique_journaliere(
                date_cible=date_debut,
                planificateur_id=user_id
            )
            return JsonResponse(resultat)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la planification rapide: {str(e)}'
        })

@planificateur_required_api
@require_http_methods(["GET"])
def suggestions_regroupements_api(request):
    """API pour obtenir des suggestions de regroupements"""
    try:
        date_cible = request.GET.get('date')
        if date_cible:
            date_obj = datetime.strptime(date_cible, '%Y-%m-%d').date()
        else:
            date_obj = timezone.now().date()
        
        suggestions = PlanificationService.suggerer_regroupements(date_obj)
        
        # Formater les suggestions pour l'affichage
        suggestions_formatees = []
        for suggestion in suggestions:
            commandes_info = []
            for cmd in suggestion['commandes']:
                commandes_info.append({
                    'id': cmd.id,
                    'client': cmd.client.get_full_name(),
                    'origine': cmd.origine,
                    'destination': cmd.destination,
                    'poids': float(cmd.poids),
                    'priorite': cmd.priorite
                })
            
            suggestions_formatees.append({
                'zone': suggestion['zone'],
                'commandes': commandes_info,
                'nb_commandes': len(commandes_info),
                'poids_total': suggestion['poids_total'],
                'vehicule_recommande': suggestion['vehicule_recommande'],
                'economies_estimees': suggestion['economies_estimees'],
                'score_optimisation': suggestion['score_optimisation']
            })
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions_formatees,
            'date_analyse': date_obj.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de l\'analyse: {str(e)}'
        })

@planificateur_required_api
@require_http_methods(["POST"])
def appliquer_regroupement_api(request):
    """API pour appliquer un regroupement suggéré"""
    try:
        data = json.loads(request.body)
        user_id = request.session['user_id']
        
        commandes_ids = data.get('commandes_ids', [])
        vehicule_type = data.get('vehicule_type', 'camionnette')
        date_debut = data.get('date_debut')
        nom_tournee = data.get('nom_tournee', f'Regroupement {timezone.now().strftime("%d/%m %H:%M")}')
        
        if not commandes_ids:
            return JsonResponse({
                'success': False,
                'message': 'Aucune commande spécifiée'
            })
        
        # Récupérer les commandes
        commandes = Commande.objects.filter(
            id__in=commandes_ids,
            statut='en_attente'
        ).select_related('client')
        
        if not commandes.exists():
            return JsonResponse({
                'success': False,
                'message': 'Aucune commande valide trouvée'
            })
        
        # Trouver un véhicule approprié
        poids_total = sum(float(cmd.poids) for cmd in commandes)
        
        vehicule = Vehicule.objects.filter(
            type_vehicule=vehicule_type,
            disponible=True,
            capacite_max__gte=poids_total
        ).select_related('transporteur').first()
        
        if not vehicule:
            return JsonResponse({
                'success': False,
                'message': f'Aucun véhicule {vehicule_type} disponible avec une capacité suffisante'
            })
        
        # Créer la tournée
        date_debut_dt = datetime.strptime(date_debut, '%Y-%m-%dT%H:%M')
        date_debut_dt = timezone.make_aware(date_debut_dt)
        
        with transaction.atomic():
            duree_estimee = timedelta(minutes=len(commandes) * 30 + 120)
            
            tournee = Tournee.objects.create(
                nom=nom_tournee,
                planificateur_id=user_id,
                transporteur=vehicule.transporteur,
                vehicule=vehicule,
                date_debut_prevue=date_debut_dt,
                date_fin_prevue=date_debut_dt + duree_estimee,
                distance_totale=len(commandes) * 20,
                duree_prevue=duree_estimee,
                optimisee=True,
                notes=f'Tournée créée par regroupement automatique - {len(commandes)} commandes'
            )
            
            # Créer les étapes et mettre à jour les commandes
            heure_actuelle = date_debut_dt
            
            for i, commande in enumerate(commandes):
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
                
                heure_actuelle += timedelta(minutes=35)
                
                # Mettre à jour la commande
                commande.statut = 'planifiee'
                commande.planificateur_id = user_id
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
            
            # Notifications
            Notification.objects.create(
                utilisateur=vehicule.transporteur,
                type_notification='tournee_creee',
                titre='Nouvelle tournée par regroupement',
                message=f'Une tournée optimisée "{nom_tournee}" avec {len(commandes)} commandes vous a été assignée.',
                tournee=tournee,
                priority='high'
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Regroupement appliqué avec succès - Tournée "{nom_tournee}" créée',
            'tournee_id': tournee.id,
            'nb_commandes': len(commandes),
            'transporteur': vehicule.transporteur.get_full_name(),
            'vehicule': f'{vehicule.immatriculation} ({vehicule.get_type_vehicule_display()})'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de l\'application du regroupement: {str(e)}'
        })

@planificateur_required_api
@require_http_methods(["GET"])
def stats_planification_api(request):
    """API pour obtenir les statistiques de planification en temps réel"""
    try:
        user_id = request.session['user_id']
        
        # Statistiques générales
        stats = {
            'commandes_en_attente': Commande.objects.filter(statut='en_attente').count(),
            'commandes_planifiees_aujourd_hui': Commande.objects.filter(
                planificateur_id=user_id,
                date_creation__date=timezone.now().date(),
                statut__in=['planifiee', 'en_cours']
            ).count(),
            'tournees_actives': Tournee.objects.filter(
                planificateur_id=user_id,
                statut__in=['planifiee', 'en_cours']
            ).count(),
            'vehicules_disponibles': Vehicule.objects.filter(disponible=True).count(),
            'transporteurs_actifs': User.objects.filter(
                role='transporteur',
                is_active=True,
                vehicules__disponible=True
            ).distinct().count()
        }
        
        # Performance du planificateur
        total_planifiees = Commande.objects.filter(planificateur_id=user_id).count()
        livrees_a_temps = Commande.objects.filter(
            planificateur_id=user_id,
            statut='livree'
        ).count()
        
        taux_reussite = (livrees_a_temps / total_planifiees * 100) if total_planifiees > 0 else 0
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'performance': {
                'total_planifiees': total_planifiees,
                'livrees_a_temps': livrees_a_temps,
                'taux_reussite': round(taux_reussite, 1)
            },
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors du chargement des statistiques: {str(e)}'
        })

@planificateur_required_api
@require_http_methods(["GET"])
def transporteurs_disponibles_api(request):
    """API pour obtenir la liste des transporteurs disponibles"""
    try:
        transporteurs = User.objects.filter(
            role='transporteur',
            is_active=True
        ).prefetch_related('vehicules')
        
        transporteurs_data = []
        for transporteur in transporteurs:
            vehicules_disponibles = transporteur.vehicules.filter(disponible=True)
            
            if vehicules_disponibles.exists():
                transporteurs_data.append({
                    'id': transporteur.id,
                    'nom': transporteur.get_full_name(),
                    'email': transporteur.email,
                    'phone': transporteur.phone,
                    'vehicules_disponibles': vehicules_disponibles.count(),
                    'vehicules': [{
                        'id': v.id,
                        'immatriculation': v.immatriculation,
                        'type': v.get_type_vehicule_display(),
                        'capacite': float(v.capacite_max)
                    } for v in vehicules_disponibles]
                })
        
        return JsonResponse({
            'success': True,
            'transporteurs': transporteurs_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors du chargement: {str(e)}'
        })

@planificateur_required_api
@require_http_methods(["GET"])
def vehicules_transporteur_api(request, transporteur_id):
    """API pour obtenir les véhicules d'un transporteur"""
    try:
        transporteur = User.objects.get(id=transporteur_id, role='transporteur')
        vehicules = transporteur.vehicules.filter(disponible=True)
        
        vehicules_data = []
        for vehicule in vehicules:
            vehicules_data.append({
                'id': vehicule.id,
                'immatriculation': vehicule.immatriculation,
                'type': vehicule.get_type_vehicule_display(),
                'capacite': float(vehicule.capacite_max),
                'disponible': vehicule.disponible
            })
        
        return JsonResponse({
            'success': True,
            'vehicules': vehicules_data
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Transporteur introuvable'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })

@planificateur_required_api
@require_http_methods(["POST"])
def optimiser_tournee_existante_api(request, tournee_id):
    """API pour optimiser une tournée existante"""
    try:
        user_id = request.session['user_id']
        data = json.loads(request.body)
        
        nouvelles_commandes = data.get('nouvelles_commandes', [])
        
        # Utiliser le service de planification
        resultat = PlanificationService.replanifier_tournee(
            tournee_id=tournee_id,
            nouvelles_commandes=nouvelles_commandes
        )
        
        return JsonResponse(resultat)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de l\'optimisation: {str(e)}'
        })

@planificateur_required_api
@require_http_methods(["POST"])
def planification_urgence_api(request, commande_id):
    """API pour planifier une commande en urgence"""
    try:
        user_id = request.session['user_id']
        
        commande = Commande.objects.get(id=commande_id, statut='en_attente')
        
        # Trouver le véhicule le plus proche et disponible
        vehicule_optimal = Vehicule.objects.filter(
            disponible=True,
            capacite_max__gte=commande.poids
        ).select_related('transporteur').first()
        
        if not vehicule_optimal:
            return JsonResponse({
                'success': False,
                'message': 'Aucun véhicule disponible pour cette commande urgente'
            })
        
        with transaction.atomic():
            # Créer une tournée urgente
            date_debut = timezone.now() + timedelta(minutes=30)
            
            tournee_urgente = Tournee.objects.create(
                nom=f'URGENCE - Commande #{commande.id}',
                planificateur_id=user_id,
                transporteur=vehicule_optimal.transporteur,
                vehicule=vehicule_optimal,
                date_debut_prevue=date_debut,
                date_fin_prevue=date_debut + timedelta(hours=2),
                distance_totale=50,
                duree_prevue=timedelta(hours=2),
                optimisee=False,
                notes='Tournée créée en urgence'
            )
            
            # Créer l'étape de livraison
            EtapeTournee.objects.create(
                tournee=tournee_urgente,
                commande=commande,
                ordre=1,
                type_etape='livraison',
                adresse=commande.destination,
                heure_prevue=date_debut + timedelta(minutes=30),
                duree_prevue=timedelta(minutes=20)
            )
            
            # Mettre à jour la commande
            commande.statut = 'planifiee'
            commande.priorite = 'urgente'
            commande.planificateur_id = user_id
            commande.transporteur = vehicule_optimal.transporteur
            commande.date_livraison_planifiee = date_debut + timedelta(minutes=30)
            commande.save()
            
            # Créer la livraison
            Livraison.objects.create(
                commande=commande,
                vehicule=vehicule_optimal,
                tournee=tournee_urgente,
                statut='en_attente'
            )
            
            # Marquer le véhicule comme occupé
            vehicule_optimal.disponible = False
            vehicule_optimal.save()
            
            # Notifications urgentes
            Notification.objects.create(
                utilisateur=vehicule_optimal.transporteur,
                type_notification='tournee_creee',
                titre='🚨 TOURNÉE URGENTE ASSIGNÉE',
                message=f'Une livraison urgente (Commande #{commande.id}) vous a été assignée. Départ prévu dans 30 minutes.',
                tournee=tournee_urgente,
                priority='urgent'
            )
            
            Notification.objects.create(
                utilisateur=commande.client,
                type_notification='commande_planifiee',
                titre='Commande planifiée en urgence',
                message=f'Votre commande #{commande.id} a été planifiée en urgence. Livraison prévue dans 1h.',
                commande=commande,
                tournee=tournee_urgente,
                priority='high'
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Commande #{commande.id} planifiée en urgence',
            'tournee_id': tournee_urgente.id,
            'transporteur': vehicule_optimal.transporteur.get_full_name(),
            'vehicule': vehicule_optimal.immatriculation,
            'heure_livraison': (date_debut + timedelta(minutes=30)).strftime('%H:%M')
        })
        
    except Commande.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Commande introuvable'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la planification urgente: {str(e)}'
        })