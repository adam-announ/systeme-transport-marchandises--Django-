# transport/utils.py - Version corrigée avec fonctions manquantes

import math
import random
from datetime import datetime, timedelta
from django.utils import timezone
from .models import DonneesMeteo, DonneesTrafic, Itineraire

def calculer_distance(lat1, lon1, lat2, lon2):
    """Calculer la distance entre deux points GPS en kilomètres"""
    if not all([lat1, lon1, lat2, lon2]):
        return 50  # Distance par défaut si coordonnées manquantes
    
    R = 6371  # Rayon de la Terre en kilomètres
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return round(distance, 1)

def calculer_itineraire_optimise(adresse_depart, adresse_arrivee):
    """Calculer l'itinéraire optimal entre deux adresses"""
    coords_villes = {
        'Casablanca': (33.5731, -7.5898),
        'Rabat': (33.9716, -6.8498),
        'Marrakech': (31.6295, -7.9811),
        'Fès': (34.0331, -5.0003),
        'Tanger': (35.7595, -5.8340),
        'Agadir': (30.4278, -9.5981),
        'Meknès': (33.8731, -5.5547),
        'Oujda': (34.6814, -1.9086),
    }
    
    ville_depart = adresse_depart.ville
    ville_arrivee = adresse_arrivee.ville
    
    if ville_depart in coords_villes and ville_arrivee in coords_villes:
        lat1, lon1 = coords_villes[ville_depart]
        lat2, lon2 = coords_villes[ville_arrivee]
    else:
        lat1 = adresse_depart.latitude or 33.5731
        lon1 = adresse_depart.longitude or -7.5898
        lat2 = adresse_arrivee.latitude or 33.5731
        lon2 = adresse_arrivee.longitude or -7.5898
    
    distance = calculer_distance(lat1, lon1, lat2, lon2)
    temps_estime = int(distance / 60 * 60)  # Vitesse moyenne 60 km/h
    
    return {
        'distance': distance,
        'temps_estime': temps_estime,
        'points': [
            {'lat': lat1, 'lon': lon1, 'adresse': str(adresse_depart)},
            {'lat': lat2, 'lon': lon2, 'adresse': str(adresse_arrivee)}
        ],
        'instructions': generer_instructions_route(adresse_depart, adresse_arrivee, distance),
        'type_route': 'autoroute' if distance > 100 else 'nationale'
    }

def generer_instructions_route(depart, arrivee, distance):
    """Générer des instructions de navigation"""
    instructions = [
        {
            'step': 1,
            'instruction': f"Départ de {depart.rue}, {depart.ville}",
            'distance': 0
        }
    ]
    
    if distance > 50:
        instructions.extend([
            {
                'step': 2,
                'instruction': "Prendre l'autoroute A1",
                'distance': 5
            },
            {
                'step': 3,
                'instruction': f"Continuer sur {distance - 10} km",
                'distance': distance - 5
            },
            {
                'step': 4,
                'instruction': "Sortir de l'autoroute",
                'distance': distance - 5
            }
        ])
    else:
        instructions.append({
            'step': 2,
            'instruction': "Suivre la route nationale",
            'distance': distance / 2
        })
    
    instructions.append({
        'step': len(instructions) + 1,
        'instruction': f"Arrivée à {arrivee.rue}, {arrivee.ville}",
        'distance': distance
    })
    
    return instructions

def obtenir_donnees_meteo(adresse_depart, adresse_arrivee):
    """Obtenir les données météo pour un trajet"""
    conditions_possibles = ['ENSOLEILLE', 'NUAGEUX', 'PLUIE', 'BROUILLARD']
    condition = random.choice(conditions_possibles)
    
    donnees = {
        'temperature': random.randint(10, 35),
        'conditions': condition,
        'vent_vitesse': random.randint(5, 30),
        'visibilite': 10000 if condition != 'BROUILLARD' else random.randint(100, 500),
        'alerte': condition in ['PLUIE', 'BROUILLARD']
    }
    
    # Enregistrer dans la base
    try:
        DonneesMeteo.objects.create(
            zone=f"{adresse_depart.ville} - {adresse_arrivee.ville}",
            temperature=donnees['temperature'],
            conditions=condition,
            vent_vitesse=donnees['vent_vitesse'],
            visibilite=donnees['visibilite'],
            alerte=donnees['alerte'],
            niveau_alerte='haute' if condition == 'BROUILLARD' else 'moyenne' if condition == 'PLUIE' else '',
            description=f"Conditions {condition} sur le trajet"
        )
    except Exception:
        pass  # Ignorer les erreurs de base de données
    
    return donnees

def obtenir_donnees_trafic(adresse_depart, adresse_arrivee):
    """Obtenir les données de trafic pour un trajet"""
    heure_actuelle = datetime.now().hour
    
    if 7 <= heure_actuelle <= 9 or 17 <= heure_actuelle <= 19:
        niveau = random.choice(['DENSE', 'NORMAL', 'DENSE'])
    else:
        niveau = random.choice(['FLUIDE', 'NORMAL', 'FLUIDE'])
    
    vitesses = {
        'FLUIDE': 80,
        'NORMAL': 60,
        'DENSE': 40,
        'BLOQUE': 20
    }
    
    donnees = {
        'niveau': niveau,
        'vitesse_moyenne': vitesses[niveau],
        'temps_retard': 0 if niveau == 'FLUIDE' else 10 if niveau == 'NORMAL' else 20
    }
    
    try:
        DonneesTrafic.objects.create(
            zone=f"{adresse_depart.ville} - {adresse_arrivee.ville}",
            niveau=niveau,
            vitesse_moyenne=donnees['vitesse_moyenne'],
            temps_retard=donnees['temps_retard']
        )
    except Exception:
        pass
    
    return donnees

def calculer_score_transporteur(transporteur, commande):
    """Calculer un score pour évaluer l'adéquation d'un transporteur"""
    score = 100
    
    # Capacité de charge
    if transporteur.capacite_charge < commande.poids:
        return 0
    elif transporteur.capacite_charge < commande.poids * 1.5:
        score -= 10
    
    # Missions en cours
    missions_actives = transporteur.missiontransporteur_set.filter(
        statut='EN_COURS'
    ).count()
    score -= missions_actives * 15
    
    # Distance du transporteur
    if transporteur.latitude_actuelle and transporteur.longitude_actuelle:
        try:
            distance = calculer_distance(
                transporteur.latitude_actuelle,
                transporteur.longitude_actuelle,
                commande.adresse_enlevement.latitude or 33.5731,
                commande.adresse_enlevement.longitude or -7.5898
            )
            if distance > 50:
                score -= 20
            elif distance > 20:
                score -= 10
        except Exception:
            pass
    
    # Taux de réussite historique
    missions_terminees = transporteur.missiontransporteur_set.filter(
        statut='TERMINEE'
    ).count()
    missions_totales = transporteur.missiontransporteur_set.count()
    
    if missions_totales > 0:
        taux_reussite = (missions_terminees / missions_totales) * 100
        if taux_reussite < 80:
            score -= 15
        elif taux_reussite > 95:
            score += 10
    
    # Priorité de la commande
    if commande.priorite == 2 and missions_actives == 0:
        score += 20
    
    return max(0, score)

# Fonctions manquantes ajoutées

def recuperer_alertes_actuelles():
    """Récupérer les alertes météo et trafic actuelles"""
    alertes = []
    
    # Alertes météo récentes
    try:
        alertes_meteo = DonneesMeteo.objects.filter(
            alerte=True,
            date_creation__gte=timezone.now() - timedelta(hours=6)
        ).order_by('-date_creation')[:5]
        
        for alerte in alertes_meteo:
            alertes.append({
                'type': 'meteo',
                'niveau': alerte.niveau_alerte or 'moyenne',
                'message': alerte.description or f"Conditions {alerte.get_conditions_display()}",
                'zone': alerte.zone,
                'heure': alerte.date_creation
            })
    except Exception:
        pass
    
    # Alertes trafic récentes
    try:
        alertes_trafic = DonneesTrafic.objects.filter(
            niveau__in=['DENSE', 'BLOQUE'],
            date_creation__gte=timezone.now() - timedelta(hours=1)
        ).order_by('-date_creation')[:5]
        
        for alerte in alertes_trafic:
            alertes.append({
                'type': 'trafic',
                'niveau': alerte.niveau.lower(),
                'message': f"Trafic {alerte.get_niveau_display()} - {alerte.zone}",
                'zone': alerte.zone,
                'heure': alerte.date_creation
            })
    except Exception:
        pass
    
    return sorted(alertes, key=lambda x: x['heure'], reverse=True)

def suggerer_transporteurs(commande):
    """Suggérer les meilleurs transporteurs pour une commande"""
    from .models import Transporteur
    
    transporteurs = Transporteur.objects.filter(
        disponible=True,
        capacite_charge__gte=commande.poids,
        actif=True
    )
    
    transporteurs_scores = []
    for transporteur in transporteurs:
        score = calculer_score_transporteur(transporteur, commande)
        if score > 0:
            transporteurs_scores.append({
                'transporteur': transporteur,
                'score': score,
                'missions_actives': transporteur.missiontransporteur_set.filter(
                    statut='EN_COURS'
                ).count(),
                'taux_reussite': transporteur.taux_reussite
            })
    
    # Trier par score décroissant
    transporteurs_scores.sort(key=lambda x: x['score'], reverse=True)
    
    return transporteurs_scores[:5]

def identifier_zones_actives():
    """Identifier les zones avec le plus d'activité"""
    from django.db.models import Count
    from .models import MissionTransporteur
    
    try:
        zones = MissionTransporteur.objects.filter(
            statut__in=['ASSIGNEE', 'EN_COURS']
        ).values('commande__adresse_livraison__ville').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return [zone['commande__adresse_livraison__ville'] for zone in zones if zone['commande__adresse_livraison__ville']]
    except Exception:
        return ['Casablanca', 'Rabat', 'Marrakech']  # Valeurs par défaut

def obtenir_villes_avec_missions():
    """Obtenir la liste des villes avec des missions actives"""
    from .models import MissionTransporteur
    
    try:
        villes_depart = set(MissionTransporteur.objects.filter(
            statut__in=['ASSIGNEE', 'EN_COURS']
        ).values_list('commande__adresse_enlevement__ville', flat=True))
        
        villes_arrivee = set(MissionTransporteur.objects.filter(
            statut__in=['ASSIGNEE', 'EN_COURS']
        ).values_list('commande__adresse_livraison__ville', flat=True))
        
        return list(villes_depart.union(villes_arrivee))
    except Exception:
        return ['Casablanca', 'Rabat', 'Marrakech', 'Fès']

def obtenir_donnees_trafic_zone(zone):
    """Obtenir les données de trafic pour une zone spécifique"""
    niveaux = ['FLUIDE', 'NORMAL', 'DENSE', 'BLOQUE']
    niveau = random.choice(niveaux)
    
    vitesses = {
        'FLUIDE': 80,
        'NORMAL': 60,
        'DENSE': 40,
        'BLOQUE': 20
    }
    
    try:
        DonneesTrafic.objects.create(
            zone=zone,
            niveau=niveau,
            vitesse_moyenne=vitesses[niveau]
        )
    except Exception:
        pass
    
    return {
        'niveau': niveau.lower(),
        'vitesse_moyenne': vitesses[niveau],
        'incidents': []
    }

def obtenir_donnees_meteo_ville(ville):
    """Obtenir les données météo pour une ville"""
    conditions = ['ENSOLEILLE', 'NUAGEUX', 'PLUIE', 'NEIGE', 'BROUILLARD']
    condition = random.choice(conditions)
    
    try:
        meteo = DonneesMeteo.objects.create(
            zone=ville,
            temperature=random.randint(5, 30),
            conditions=condition,
            vent_vitesse=random.randint(5, 50),
            visibilite=random.randint(500, 10000),
            alerte=condition in ['NEIGE', 'BROUILLARD'],
            niveau_alerte='haute' if condition == 'NEIGE' else 'moyenne'
        )
        
        return {
            'temperature': meteo.temperature,
            'conditions': condition.lower(),
            'vent': f"{meteo.vent_vitesse} km/h",
            'visibilite': f"{meteo.visibilite} m",
            'alertes': [f'Vigilance {condition.lower()}'] if meteo.alerte else []
        }
    except Exception:
        return {
            'temperature': 20,
            'conditions': 'normal',
            'vent': '10 km/h',
            'visibilite': '10000 m',
            'alertes': []
        }

def envoyer_notification_push(user, titre, message, type_notif='info'):
    """Envoyer une notification push à un utilisateur"""
    from .models import Notification
    
    try:
        notification = Notification.objects.create(
            destinataire=user,
            type='SYSTEME',
            titre=titre,
            message=message,
            priorite='HAUTE' if type_notif == 'urgent' else 'NORMALE'
        )
        return notification
    except Exception:
        return None

def calculer_prix_estimation(poids, distance, type_marchandise='standard'):
    """Calculer une estimation de prix pour une commande"""
    prix_base = 50
    prix_kg = 2
    prix_km = 1.5
    
    multiplicateurs = {
        'standard': 1.0,
        'fragile': 1.3,
        'perissable': 1.5,
        'dangereux': 2.0,
    }
    
    multiplicateur = multiplicateurs.get(type_marchandise.lower(), 1.0)
    prix_total = (prix_base + (poids * prix_kg) + (distance * prix_km)) * multiplicateur
    
    return round(prix_total, 2)