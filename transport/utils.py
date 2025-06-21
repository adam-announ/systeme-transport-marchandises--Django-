# transport/utils.py
import math
import random
from datetime import datetime, timedelta
from django.utils import timezone
from .models import DonneesMeteo, DonneesTrafic, Itineraire

def calculer_distance(lat1, lon1, lat2, lon2):
    """
    Calculer la distance entre deux points GPS en kilomètres
    en utilisant la formule de Haversine
    """
    # Rayon de la Terre en kilomètres
    R = 6371
    
    # Convertir en radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Formule de Haversine
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return round(distance, 1)

def calculer_itineraire_optimise(adresse_depart, adresse_arrivee):
    """
    Calculer l'itinéraire optimal entre deux adresses
    """
    # En production, utiliser une vraie API de géocodage/routing
    # Ici, on simule les coordonnées GPS
    
    # Coordonnées simulées pour Casablanca et environs
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
    
    # Récupérer ou simuler les coordonnées
    ville_depart = adresse_depart.ville
    ville_arrivee = adresse_arrivee.ville
    
    if ville_depart in coords_villes and ville_arrivee in coords_villes:
        lat1, lon1 = coords_villes[ville_depart]
        lat2, lon2 = coords_villes[ville_arrivee]
    else:
        # Coordonnées aléatoires autour de Casablanca
        lat1 = 33.5731 + random.uniform(-0.5, 0.5)
        lon1 = -7.5898 + random.uniform(-0.5, 0.5)
        lat2 = 33.5731 + random.uniform(-0.5, 0.5)
        lon2 = -7.5898 + random.uniform(-0.5, 0.5)
    
    # Calculer la distance
    distance = calculer_distance(lat1, lon1, lat2, lon2)
    
    # Estimer le temps (vitesse moyenne 60 km/h)
    temps_estime = int(distance / 60 * 60)  # en minutes
    
    # Créer l'itinéraire
    itineraire = {
        'distance': distance,
        'temps_estime': temps_estime,
        'points': [
            {'lat': lat1, 'lon': lon1, 'adresse': str(adresse_depart)},
            {'lat': lat2, 'lon': lon2, 'adresse': str(adresse_arrivee)}
        ],
        'instructions': generer_instructions_route(adresse_depart, adresse_arrivee, distance),
        'type_route': 'autoroute' if distance > 100 else 'nationale'
    }
    
    return itineraire

def generer_instructions_route(depart, arrivee, distance):
    """Générer des instructions de navigation"""
    instructions = []
    
    instructions.append({
        'step': 1,
        'instruction': f"Départ de {depart.rue}, {depart.ville}",
        'distance': 0
    })
    
    if distance > 50:
        instructions.append({
            'step': 2,
            'instruction': "Prendre l'autoroute A1",
            'distance': 5
        })
        
        instructions.append({
            'step': 3,
            'instruction': f"Continuer sur {distance - 10} km",
            'distance': distance - 5
        })
        
        instructions.append({
            'step': 4,
            'instruction': "Sortir de l'autoroute",
            'distance': distance - 5
        })
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
    # En production, utiliser une vraie API météo
    # Simulation des données
    
    conditions_possibles = ['ensoleille', 'nuageux', 'pluie', 'brouillard']
    condition = random.choice(conditions_possibles)
    
    donnees = {
        'temperature': random.randint(10, 35),
        'conditions': condition,
        'vent_vitesse': random.randint(5, 30),
        'visibilite': 10000 if condition != 'brouillard' else random.randint(100, 500),
        'alerte': condition in ['pluie', 'brouillard']
    }
    
    # Enregistrer dans la base
    DonneesMeteo.objects.create(
        zone=f"{adresse_depart.ville} - {adresse_arrivee.ville}",
        temperature=donnees['temperature'],
        conditions=condition,
        vent_vitesse=donnees['vent_vitesse'],
        visibilite=donnees['visibilite'],
        alerte=donnees['alerte'],
        niveau_alerte='haute' if condition == 'brouillard' else 'moyenne' if condition == 'pluie' else '',
        description=f"Conditions {condition} sur le trajet"
    )
    
    return donnees

def obtenir_donnees_trafic(adresse_depart, adresse_arrivee):
    """Obtenir les données de trafic pour un trajet"""
    # En production, utiliser une vraie API trafic
    # Simulation des données
    
    heure_actuelle = datetime.now().hour
    
    # Heures de pointe
    if 7 <= heure_actuelle <= 9 or 17 <= heure_actuelle <= 19:
        niveau = random.choice(['dense', 'normal', 'dense'])
    else:
        niveau = random.choice(['fluide', 'normal', 'fluide'])
    
    vitesses = {
        'fluide': 80,
        'normal': 60,
        'dense': 40,
        'bloque': 20
    }
    
    donnees = {
        'niveau': niveau,
        'vitesse_moyenne': vitesses[niveau],
        'temps_retard': 0 if niveau == 'fluide' else 10 if niveau == 'normal' else 20
    }
    
    # Enregistrer dans la base
    DonneesTrafic.objects.create(
        zone=f"{adresse_depart.ville} - {adresse_arrivee.ville}",
        niveau=niveau,
        vitesse_moyenne=donnees['vitesse_moyenne'],
        temps_retard=donnees['temps_retard']
    )
    
    return donnees

def calculer_score_transporteur(transporteur, commande):
    """
    Calculer un score pour évaluer l'adéquation d'un transporteur à une commande
    Score sur 100 points
    """
    score = 100
    
    # Capacité de charge
    if transporteur.capacite_charge < commande.poids:
        return 0  # Ne peut pas prendre la commande
    elif transporteur.capacite_charge < commande.poids * 1.5:
        score -= 10  # Proche de la limite
    
    # Missions en cours
    missions_actives = transporteur.missiontransporteur_set.filter(
        statut='EN_COURS'
    ).count()
    score -= missions_actives * 15  # -15 points par mission active
    
    # Distance du transporteur (si position disponible)
    if transporteur.latitude_actuelle and transporteur.longitude_actuelle:
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
    if commande.priorite == 2:  # Urgente
        # Privilégier les transporteurs sans mission active
        if missions_actives == 0:
            score += 20
    
    return max(0, score)

def envoyer_notification_push(user, titre, message, type_notif='info'):
    """
    Envoyer une notification push à un utilisateur
    En production, utiliser un service comme Firebase Cloud Messaging
    """
    # Simulation - enregistrer seulement dans la base
    from .models import Notification
    
    notification = Notification.objects.create(
        destinataire=user,
        type='SYSTEME',
        titre=titre,
        message=message,
        priorite='HAUTE' if type_notif == 'urgent' else 'NORMALE'
    )
    
    # En production, appeler l'API de notification push ici
    
    return notification

def optimiser_tournee_transporteur(transporteur, missions):
    """
    Optimiser l'ordre des missions d'un transporteur
    Utilise un algorithme glouton simple
    """
    if not missions:
        return []
    
    missions_list = list(missions)
    tournee_optimisee = []
    
    # Position de départ (position actuelle du transporteur ou première mission)
    if transporteur.latitude_actuelle and transporteur.longitude_actuelle:
        position_actuelle = (transporteur.latitude_actuelle, transporteur.longitude_actuelle)
    else:
        premiere_mission = missions_list[0]
        position_actuelle = (
            premiere_mission.commande.adresse_enlevement.latitude or 33.5731,
            premiere_mission.commande.adresse_enlevement.longitude or -7.5898
        )
    
    missions_restantes = missions_list.copy()
    
    while missions_restantes:
        # Trouver la mission la plus proche
        mission_proche = None
        distance_min = float('inf')
        
        for mission in missions_restantes:
            lat = mission.commande.adresse_enlevement.latitude or 33.5731
            lon = mission.commande.adresse_enlevement.longitude or -7.5898
            
            distance = calculer_distance(
                position_actuelle[0],
                position_actuelle[1],
                lat,
                lon
            )
            
            # Prioriser les missions urgentes
            if mission.commande.priorite == 2:
                distance *= 0.5  # Réduire artificiellement la distance
            
            if distance < distance_min:
                distance_min = distance
                mission_proche = mission
        
        if mission_proche:
            tournee_optimisee.append(mission_proche)
            missions_restantes.remove(mission_proche)
            
            # Mettre à jour la position actuelle
            position_actuelle = (
                mission_proche.commande.adresse_livraison.latitude or 33.5731,
                mission_proche.commande.adresse_livraison.longitude or -7.5898
            )
    
    return tournee_optimisee

def generer_rapport_performance(transporteur, date_debut, date_fin):
    """Générer un rapport de performance pour un transporteur"""
    from django.db.models import Count, Avg, Sum, Q
    
    missions = transporteur.missiontransporteur_set.filter(
        date_assignation__range=[date_debut, date_fin]
    )
    
    rapport = {
        'transporteur': transporteur,
        'periode': {
            'debut': date_debut,
            'fin': date_fin
        },
        'statistiques': {
            'total_missions': missions.count(),
            'missions_terminees': missions.filter(statut='TERMINEE').count(),
            'missions_annulees': missions.filter(statut='ANNULEE').count(),
            'distance_totale': missions.aggregate(Sum('distance_parcourue'))['distance_parcourue__sum'] or 0,
            'temps_moyen_mission': None,  # À calculer
            'taux_reussite': 0,
            'incidents': 0
        },
        'details_missions': []
    }
    
    # Calculer le taux de réussite
    if rapport['statistiques']['total_missions'] > 0:
        rapport['statistiques']['taux_reussite'] = round(
            (rapport['statistiques']['missions_terminees'] / rapport['statistiques']['total_missions']) * 100,
            1
        )
    
    # Compter les incidents
    from .models import Incident
    rapport['statistiques']['incidents'] = Incident.objects.filter(
        transporteur=transporteur,
        date_signalement__range=[date_debut, date_fin]
    ).count()
    
    # Temps moyen par mission
    missions_terminees = missions.filter(statut='TERMINEE', date_fin__isnull=False)
    if missions_terminees.exists():
        temps_total = 0
        for mission in missions_terminees:
            if mission.date_debut and mission.date_fin:
                duree = (mission.date_fin - mission.date_debut).total_seconds() / 60  # en minutes
                temps_total += duree
        
        if missions_terminees.count() > 0:
            rapport['statistiques']['temps_moyen_mission'] = round(
                temps_total / missions_terminees.count()
            )
    
    return rapport

def estimer_temps_livraison(commande, transporteur=None):
    """
    Estimer le temps de livraison pour une commande
    """
    # Calculer la distance
    itineraire = calculer_itineraire_optimise(
        commande.adresse_enlevement,
        commande.adresse_livraison
    )
    
    temps_base = itineraire['temps_estime']
    
    # Ajustements selon les conditions
    meteo = obtenir_donnees_meteo(
        commande.adresse_enlevement,
        commande.adresse_livraison
    )
    
    trafic = obtenir_donnees_trafic(
        commande.adresse_enlevement,
        commande.adresse_livraison
    )
    
    # Ajustement météo
    if meteo['conditions'] in ['pluie', 'brouillard']:
        temps_base *= 1.2
    
    # Ajustement trafic
    temps_base += trafic.get('temps_retard', 0)
    
    # Ajustement selon le transporteur
    if transporteur:
        # Si le transporteur a d'autres missions
        missions_actives = transporteur.missiontransporteur_set.filter(
            statut='EN_COURS'
        ).count()
        temps_base += missions_actives * 30  # 30 min par mission active
    
    # Ajouter temps de chargement/déchargement
    temps_base += 30  # 15 min chargement + 15 min déchargement
    
    return {
        'temps_estime_minutes': round(temps_base),
        'heure_livraison_estimee': timezone.now() + timedelta(minutes=temps_base),
        'facteurs': {
            'distance': itineraire['distance'],
            'meteo': meteo['conditions'],
            'trafic': trafic['niveau']
        }
    }