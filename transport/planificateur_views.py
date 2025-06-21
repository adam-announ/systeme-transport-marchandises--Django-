# transport/planificateur_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Avg
from django.utils import timezone
import json
import requests
from datetime import datetime, timedelta
from .models import (
    Commande, Transporteur, MissionTransporteur, 
    Itineraire, DonneesMeteo, DonneesTrafic, Notification
)
from .utils import (
    calculer_itineraire_optimise, 
    obtenir_donnees_meteo, 
    obtenir_donnees_trafic,
    calculer_score_transporteur
)

@staff_member_required
def dashboard_planificateur(request):
    """Tableau de bord du planificateur"""
    # Statistiques
    stats = {
        'commandes_en_attente': Commande.objects.filter(statut='EN_ATTENTE').count(),
        'transporteurs_disponibles': Transporteur.objects.filter(disponible=True).count(),
        'missions_en_cours': MissionTransporteur.objects.filter(statut='EN_COURS').count(),
        'taux_livraison': calculer_taux_livraison_journalier(),
    }
    
    # Commandes à affecter
    commandes_a_affecter = Commande.objects.filter(
        statut='EN_ATTENTE'
    ).select_related('client', 'adresse_enlevement', 'adresse_livraison').order_by('date_creation')
    
    # Transporteurs disponibles
    transporteurs_disponibles = Transporteur.objects.filter(
        disponible=True
    ).annotate(
        missions_actives=Count('missiontransporteur', filter=Q(missiontransporteur__statut='EN_COURS'))
    ).order_by('missions_actives')
    
    # Alertes météo/trafic
    alertes = recuperer_alertes_actuelles()
    
    context = {
        'stats': stats,
        'commandes_a_affecter': commandes_a_affecter,
        'transporteurs_disponibles': transporteurs_disponibles,
        'alertes': alertes,
    }
    
    return render(request, 'transport/planificateur/dashboard.html', context)

@staff_member_required
def affecter_commande(request, commande_id):
    """Affecter une commande à un transporteur"""
    commande = get_object_or_404(Commande, id=commande_id, statut='EN_ATTENTE')
    
    if request.method == 'POST':
        transporteur_id = request.POST.get('transporteur_id')
        if transporteur_id:
            transporteur = get_object_or_404(Transporteur, id=transporteur_id, disponible=True)
            
            # Calculer l'itinéraire optimisé
            itineraire = calculer_itineraire_optimise(
                commande.adresse_enlevement,
                commande.adresse_livraison
            )
            
            # Créer la mission
            mission = MissionTransporteur.objects.create(
                commande=commande,
                transporteur=transporteur,
                itineraire_optimise=itineraire,
                statut='ASSIGNEE'
            )
            
            # Mettre à jour le statut de la commande
            commande.statut = 'AFFECTEE'
            commande.transporteur = transporteur
            commande.save()
            
            # Notifier le transporteur
            Notification.objects.create(
                destinataire=transporteur.user,
                transporteur=transporteur,
                type='MISSION',
                titre='Nouvelle mission assignée',
                message=f'Commande #{commande.id} - {commande.type_marchandise}',
                commande=commande,
                priorite='HAUTE'
            )
            
            messages.success(request, f'Commande affectée à {transporteur.user.username}')
            return redirect('dashboard_planificateur')
    
    # Suggérer les meilleurs transporteurs
    transporteurs_suggeres = suggerer_transporteurs(commande)
    
    context = {
        'commande': commande,
        'transporteurs_suggeres': transporteurs_suggeres,
    }
    
    return render(request, 'transport/planificateur/affecter_commande.html', context)

@staff_member_required
def optimiser_itineraires(request):
    """Interface d'optimisation des itinéraires"""
    if request.method == 'POST':
        missions_ids = request.POST.getlist('missions[]')
        type_optimisation = request.POST.get('type_optimisation', 'distance')
        
        missions = MissionTransporteur.objects.filter(
            id__in=missions_ids,
            statut__in=['ASSIGNEE', 'EN_COURS']
        )
        
        resultats = []
        for mission in missions:
            # Récupérer les données actuelles
            meteo = obtenir_donnees_meteo(
                mission.commande.adresse_enlevement,
                mission.commande.adresse_livraison
            )
            trafic = obtenir_donnees_trafic(
                mission.commande.adresse_enlevement,
                mission.commande.adresse_livraison
            )
            
            # Calculer le nouvel itinéraire optimisé
            nouvel_itineraire = calculer_itineraire_avance(
                mission.commande.adresse_enlevement,
                mission.commande.adresse_livraison,
                type_optimisation,
                meteo,
                trafic
            )
            
            # Comparer avec l'itinéraire actuel
            gain_temps = mission.itineraire_optimise.get('temps_estime', 0) - nouvel_itineraire['temps_estime']
            gain_distance = mission.itineraire_optimise.get('distance', 0) - nouvel_itineraire['distance']
            
            resultats.append({
                'mission': mission,
                'nouvel_itineraire': nouvel_itineraire,
                'gain_temps': gain_temps,
                'gain_distance': gain_distance,
                'meteo': meteo,
                'trafic': trafic
            })
        
        context = {
            'resultats': resultats,
            'type_optimisation': type_optimisation
        }
        
        return render(request, 'transport/planificateur/resultats_optimisation.html', context)
    
    # Afficher les missions à optimiser
    missions_actives = MissionTransporteur.objects.filter(
        statut__in=['ASSIGNEE', 'EN_COURS']
    ).select_related('commande', 'transporteur')
    
    context = {
        'missions_actives': missions_actives
    }
    
    return render(request, 'transport/planificateur/optimiser_itineraires.html', context)

@staff_member_required
def donnees_trafic(request):
    """Visualiser les données de trafic en temps réel"""
    # Récupérer les zones avec le plus de missions actives
    zones_actives = identifier_zones_actives()
    
    # Pour chaque zone, obtenir les données de trafic
    donnees_zones = []
    for zone in zones_actives:
        trafic_data = obtenir_donnees_trafic_zone(zone)
        donnees_zones.append({
            'zone': zone,
            'niveau_trafic': trafic_data.get('niveau', 'normal'),
            'vitesse_moyenne': trafic_data.get('vitesse_moyenne', 50),
            'incidents': trafic_data.get('incidents', [])
        })
    
    context = {
        'donnees_zones': donnees_zones,
        'derniere_maj': timezone.now()
    }
    
    return render(request, 'transport/planificateur/donnees_trafic.html', context)

@staff_member_required
def donnees_meteo(request):
    """Visualiser les données météo"""
    # Récupérer les villes avec des missions
    villes = obtenir_villes_avec_missions()
    
    donnees_meteo = []
    for ville in villes:
        meteo = obtenir_donnees_meteo_ville(ville)
        donnees_meteo.append({
            'ville': ville,
            'temperature': meteo.get('temperature'),
            'conditions': meteo.get('conditions'),
            'vent': meteo.get('vent'),
            'visibilite': meteo.get('visibilite'),
            'alertes': meteo.get('alertes', [])
        })
    
    context = {
        'donnees_meteo': donnees_meteo,
        'derniere_maj': timezone.now()
    }
    
    return render(request, 'transport/planificateur/donnees_meteo.html', context)

@staff_member_required
def api_donnees_temps_reel(request):
    """API pour obtenir les données en temps réel (AJAX)"""
    type_donnees = request.GET.get('type', 'all')
    
    data = {}
    
    if type_donnees in ['all', 'missions']:
        data['missions'] = {
            'en_cours': MissionTransporteur.objects.filter(statut='EN_COURS').count(),
            'assignees': MissionTransporteur.objects.filter(statut='ASSIGNEE').count(),
            'terminees_jour': MissionTransporteur.objects.filter(
                statut='TERMINEE',
                date_fin__date=timezone.now().date()
            ).count()
        }
    
    if type_donnees in ['all', 'transporteurs']:
        data['transporteurs'] = {
            'disponibles': Transporteur.objects.filter(disponible=True).count(),
            'en_mission': Transporteur.objects.filter(
                missiontransporteur__statut='EN_COURS'
            ).distinct().count()
        }
    
    if type_donnees in ['all', 'alertes']:
        data['alertes'] = {
            'meteo': DonneesMeteo.objects.filter(
                alerte=True,
                date_creation__gte=timezone.now() - timedelta(hours=1)
            ).count(),
            'trafic': DonneesTrafic.objects.filter(
                niveau__in=['dense', 'bloque'],
                date_creation__gte=timezone.now() - timedelta(minutes=30)
            ).count()
        }
    
    return JsonResponse(data)

# Fonctions utilitaires

def calculer_taux_livraison_journalier():
    """Calculer le taux de livraison du jour"""
    aujourd_hui = timezone.now().date()
    
    missions_jour = MissionTransporteur.objects.filter(
        date_assignation__date=aujourd_hui
    )
    
    if missions_jour.count() == 0:
        return 0
    
    missions_terminees = missions_jour.filter(statut='TERMINEE').count()
    
    return round((missions_terminees / missions_jour.count()) * 100, 1)

def suggerer_transporteurs(commande):
    """Suggérer les meilleurs transporteurs pour une commande"""
    transporteurs = Transporteur.objects.filter(
        disponible=True,
        capacite_charge__gte=commande.poids
    )
    
    # Calculer un score pour chaque transporteur
    transporteurs_scores = []
    for transporteur in transporteurs:
        score = calculer_score_transporteur(transporteur, commande)
        transporteurs_scores.append({
            'transporteur': transporteur,
            'score': score,
            'missions_actives': transporteur.missiontransporteur_set.filter(
                statut='EN_COURS'
            ).count(),
            'taux_reussite': calculer_taux_reussite(transporteur)
        })
    
    # Trier par score décroissant
    transporteurs_scores.sort(key=lambda x: x['score'], reverse=True)
    
    return transporteurs_scores[:5]  # Top 5

def calculer_taux_reussite(transporteur):
    """Calculer le taux de réussite d'un transporteur"""
    missions_totales = transporteur.missiontransporteur_set.filter(
        statut__in=['TERMINEE', 'ANNULEE']
    ).count()
    
    if missions_totales == 0:
        return 100
    
    missions_reussies = transporteur.missiontransporteur_set.filter(
        statut='TERMINEE'
    ).count()
    
    return round((missions_reussies / missions_totales) * 100, 1)

def recuperer_alertes_actuelles():
    """Récupérer les alertes météo et trafic actuelles"""
    alertes = []
    
    # Alertes météo
    alertes_meteo = DonneesMeteo.objects.filter(
        alerte=True,
        date_creation__gte=timezone.now() - timedelta(hours=6)
    ).order_by('-date_creation')[:5]
    
    for alerte in alertes_meteo:
        alertes.append({
            'type': 'meteo',
            'niveau': alerte.niveau_alerte,
            'message': alerte.description,
            'zone': alerte.zone,
            'heure': alerte.date_creation
        })
    
    # Alertes trafic
    alertes_trafic = DonneesTrafic.objects.filter(
        niveau__in=['dense', 'bloque'],
        date_creation__gte=timezone.now() - timedelta(hours=1)
    ).order_by('-date_creation')[:5]
    
    for alerte in alertes_trafic:
        alertes.append({
            'type': 'trafic',
            'niveau': alerte.niveau,
            'message': f"Trafic {alerte.niveau} - {alerte.zone}",
            'zone': alerte.zone,
            'heure': alerte.date_creation
        })
    
    return sorted(alertes, key=lambda x: x['heure'], reverse=True)

def calculer_itineraire_avance(depart, arrivee, type_optimisation, meteo, trafic):
    """Calculer un itinéraire avec optimisation avancée"""
    # Simulation d'un calcul d'itinéraire optimisé
    # En réalité, ceci utiliserait une API de cartographie
    
    distance_base = 50  # km (simulation)
    temps_base = 60  # minutes
    
    # Ajustements selon les conditions
    if meteo and meteo.get('conditions') in ['pluie', 'neige']:
        temps_base *= 1.3  # 30% de temps en plus
    
    if trafic and trafic.get('niveau') == 'dense':
        temps_base *= 1.2  # 20% de temps en plus
    elif trafic and trafic.get('niveau') == 'bloque':
        temps_base *= 1.5  # 50% de temps en plus
    
    # Optimisation selon le type
    if type_optimisation == 'temps':
        # Privilégier les voies rapides (peut augmenter la distance)
        distance_base *= 1.1
        temps_base *= 0.9
    elif type_optimisation == 'carburant':
        # Vitesse constante, éviter les arrêts
        temps_base *= 1.05
    
    return {
        'distance': round(distance_base, 1),
        'temps_estime': round(temps_base),
        'type_route': 'autoroute' if type_optimisation == 'temps' else 'nationale',
        'conditions': {
            'meteo': meteo.get('conditions') if meteo else 'normal',
            'trafic': trafic.get('niveau') if trafic else 'fluide'
        }
    }

def identifier_zones_actives():
    """Identifier les zones avec le plus d'activité"""
    from django.db.models import Count
    
    zones = MissionTransporteur.objects.filter(
        statut__in=['ASSIGNEE', 'EN_COURS']
    ).values('commande__adresse_livraison__ville').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    return [zone['commande__adresse_livraison__ville'] for zone in zones]

def obtenir_villes_avec_missions():
    """Obtenir la liste des villes avec des missions actives"""
    villes_depart = set(MissionTransporteur.objects.filter(
        statut__in=['ASSIGNEE', 'EN_COURS']
    ).values_list('commande__adresse_enlevement__ville', flat=True))
    
    villes_arrivee = set(MissionTransporteur.objects.filter(
        statut__in=['ASSIGNEE', 'EN_COURS']
    ).values_list('commande__adresse_livraison__ville', flat=True))
    
    return list(villes_depart.union(villes_arrivee))

def obtenir_donnees_trafic_zone(zone):
    """Obtenir les données de trafic pour une zone"""
    # Simulation - en réalité utiliserait une API de trafic
    import random
    
    niveaux = ['fluide', 'normal', 'dense', 'bloque']
    niveau = random.choice(niveaux)
    
    vitesses = {
        'fluide': 80,
        'normal': 60,
        'dense': 40,
        'bloque': 20
    }
    
    # Enregistrer dans la base
    DonneesTrafic.objects.create(
        zone=zone,
        niveau=niveau,
        vitesse_moyenne=vitesses[niveau]
    )
    
    return {
        'niveau': niveau,
        'vitesse_moyenne': vitesses[niveau],
        'incidents': []
    }

def obtenir_donnees_meteo_ville(ville):
    """Obtenir les données météo pour une ville"""
    # Simulation - en réalité utiliserait une API météo
    import random
    
    conditions = ['ensoleille', 'nuageux', 'pluie', 'neige', 'brouillard']
    condition = random.choice(conditions)
    
    # Enregistrer dans la base
    meteo = DonneesMeteo.objects.create(
        zone=ville,
        temperature=random.randint(5, 30),
        conditions=condition,
        vent_vitesse=random.randint(5, 50),
        visibilite=random.randint(500, 10000),
        alerte=condition in ['neige', 'brouillard'],
        niveau_alerte='haute' if condition == 'neige' else 'moyenne'
    )
    
    return {
        'temperature': meteo.temperature,
        'conditions': condition,
        'vent': f"{meteo.vent_vitesse} km/h",
        'visibilite': f"{meteo.visibilite} m",
        'alertes': ['Vigilance ' + condition] if meteo.alerte else []
    }