# transport/utils.py - Utilitaires optimisés et centralisés

import math
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

# ==========================================
# CALCULS GÉOGRAPHIQUES
# ==========================================

def calculer_distance(lat1, lon1, lat2, lon2):
    """Calculer la distance entre deux points GPS en kilomètres"""
    if not all([lat1, lon1, lat2, lon2]):
        return 50  # Distance par défaut
    
    R = 6371  # Rayon de la Terre en kilomètres
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return round(distance, 1)

def calculer_distance(adresse1, adresse2):
    """Calculer la distance entre deux adresses"""
    # Utiliser les coordonnées si disponibles
    if all([adresse1.latitude, adresse1.longitude, adresse2.latitude, adresse2.longitude]):
        return calculer_distance_coordonnees(
            adresse1.latitude, adresse1.longitude,
            adresse2.latitude, adresse2.longitude
        )
    
    # Sinon estimer par villes
    return estimer_distance_villes(adresse1.ville, adresse2.ville)

def calculer_distance_coordonnees(lat1, lon1, lat2, lon2):
    """Calculer distance avec coordonnées GPS"""
    if not all([lat1, lon1, lat2, lon2]):
        return 50
    
    R = 6371  # Rayon Terre en km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return round(R * c, 1)

def estimer_distance_villes(ville1, ville2):
    """Estimer distance entre villes marocaines"""
    distances = {
        ('Casablanca', 'Rabat'): 90,
        ('Casablanca', 'Marrakech'): 240,
        ('Casablanca', 'Fès'): 290,
        ('Casablanca', 'Tanger'): 340,
        ('Casablanca', 'Agadir'): 490,
        ('Rabat', 'Fès'): 200,
        ('Rabat', 'Marrakech'): 320,
        ('Rabat', 'Tanger'): 250,
        ('Marrakech', 'Fès'): 480,
        ('Marrakech', 'Agadir'): 250,
        ('Fès', 'Tanger'): 200,
        ('Fès', 'Oujda'): 160,
        ('Tanger', 'Tétouan'): 60,
    }
    
    # Chercher dans les deux sens
    distance = distances.get((ville1, ville2)) or distances.get((ville2, ville1))
    return distance or 100  # Distance par défaut

# ==========================================
# CALCULS D'ITINÉRAIRES
# ==========================================

def calculer_itineraire_optimise(adresse_depart, adresse_arrivee):
    """Calculer l'itinéraire optimal entre deux adresses"""
    # Cache pour éviter les recalculs
    cache_key = f"itineraire_{adresse_depart.id}_{adresse_arrivee.id}"
    itineraire = cache.get(cache_key)
    
    if itineraire:
        return itineraire
    
    # Coordonnées des principales villes
    coords_villes = {
        'Casablanca': (33.5731, -7.5898),
        'Rabat': (33.9716, -6.8498),
        'Marrakech': (31.6295, -7.9811),
        'Fès': (34.0331, -5.0003),
        'Tanger': (35.7595, -5.8340),
        'Agadir': (30.4278, -9.5981),
        'Meknès': (33.8731, -5.5547),
        'Oujda': (34.6814, -1.9086),
        'Tétouan': (35.5889, -5.3626),
    }
    
    ville_depart = adresse_depart.ville
    ville_arrivee = adresse_arrivee.ville
    
    # Utiliser coordonnées connues ou celles stockées
    if ville_depart in coords_villes:
        lat1, lon1 = coords_villes[ville_depart]
    else:
        lat1 = adresse_depart.latitude or 33.5731
        lon1 = adresse_depart.longitude or -7.5898
    
    if ville_arrivee in coords_villes:
        lat2, lon2 = coords_villes[ville_arrivee]
    else:
        lat2 = adresse_arrivee.latitude or 33.5731
        lon2 = adresse_arrivee.longitude or -7.5898
    
    distance = calculer_distance_coordonnees(lat1, lon1, lat2, lon2)
    temps_estime = calculer_temps_trajet(distance)
    
    itineraire = {
        'distance': distance,
        'temps_estime': temps_estime,
        'points': [
            {'lat': lat1, 'lon': lon1, 'adresse': str(adresse_depart)},
            {'lat': lat2, 'lon': lon2, 'adresse': str(adresse_arrivee)}
        ],
        'instructions': generer_instructions_route(adresse_depart, adresse_arrivee, distance),
        'type_route': 'autoroute' if distance > 100 else 'nationale',
        'cout_carburant': estimer_cout_carburant(distance),
        'peages': estimer_peages(distance)
    }
    
    # Cache pour 1 heure
    cache.set(cache_key, itineraire, 3600)
    
    return itineraire

def calculer_temps_trajet(distance, conditions_trafic='normal'):
    """Calculer le temps de trajet selon la distance et conditions"""
    # Vitesse moyenne selon type de route
    if distance > 100:
        vitesse_base = 80  # Autoroute
    elif distance > 50:
        vitesse_base = 70  # Route nationale
    else:
        vitesse_base = 50  # Route secondaire
    
    # Ajustements selon trafic
    multiplicateurs_trafic = {
        'fluide': 1.0,
        'normal': 1.1,
        'dense': 1.3,
        'bloque': 1.6
    }
    
    vitesse_effective = vitesse_base / multiplicateurs_trafic.get(conditions_trafic, 1.1)
    
    # Temps en minutes + pauses
    temps_base = (distance / vitesse_effective) * 60
    temps_pauses = 15 if distance > 200 else 10 if distance > 100 else 5
    
    return round(temps_base + temps_pauses)

def generer_instructions_route(depart, arrivee, distance):
    """Générer des instructions de navigation"""
    instructions = [
        {
            'etape': 1,
            'instruction': f"Départ de {depart.rue}, {depart.ville}",
            'distance': 0,
            'temps': 0
        }
    ]
    
    if distance > 100:
        instructions.extend([
            {
                'etape': 2,
                'instruction': "Prendre l'autoroute",
                'distance': 5,
                'temps': 5
            },
            {
                'etape': 3,
                'instruction': f"Continuer sur {distance - 10} km",
                'distance': distance - 5,
                'temps': calculer_temps_trajet(distance - 10)
            },
            {
                'etape': 4,
                'instruction': "Sortir de l'autoroute",
                'distance': distance - 5,
                'temps': calculer_temps_trajet(distance - 5)
            }
        ])
    elif distance > 50:
        instructions.extend([
            {
                'etape': 2,
                'instruction': "Suivre la route nationale",
                'distance': distance / 2,
                'temps': calculer_temps_trajet(distance / 2)
            }
        ])
    else:
        instructions.append({
            'etape': 2,
            'instruction': "Suivre la route locale",
            'distance': distance / 2,
            'temps': calculer_temps_trajet(distance / 2)
        })
    
    instructions.append({
        'etape': len(instructions) + 1,
        'instruction': f"Arrivée à {arrivee.rue}, {arrivee.ville}",
        'distance': distance,
        'temps': calculer_temps_trajet(distance)
    })
    
    return instructions

# ==========================================
# ESTIMATIONS DE COÛTS
# ==========================================

def estimer_cout_carburant(distance):
    """Estimer le coût en carburant"""
    # Consommation moyenne: 8L/100km pour un camion
    consommation_100km = 8
    prix_litre = 12  # MAD
    
    litres = (distance * consommation_100km) / 100
    return round(litres * prix_litre, 2)

def estimer_peages(distance):
    """Estimer les frais de péage"""
    # Péages uniquement sur autoroutes (distance > 50km)
    if distance > 50:
        return round(distance * 0.30, 2)  # 0.30 MAD/km
    return 0

def calculer_prix_estimation(poids, distance, type_marchandise='standard', priorite=0):
    """Calculer une estimation de prix complète"""
    prix_base = 50
    prix_kg = 2
    prix_km = 1.5
    
    # Multiplicateurs par type
    multiplicateurs_type = {
        'standard': 1.0,
        'fragile': 1.3,
        'perissable': 1.5,
        'dangereux': 2.0,
        'urgent': 1.8,
    }
    
    # Multiplicateurs par priorité
    multiplicateurs_priorite = {
        0: 1.0,  # Normale
        1: 1.2,  # Haute
        2: 1.5,  # Urgente
    }
    
    # Calcul de base
    prix_total = prix_base + (poids * prix_kg) + (distance * prix_km)
    
    # Application des multiplicateurs
    mult_type = multiplicateurs_type.get(type_marchandise.lower(), 1.0)
    mult_prio = multiplicateurs_priorite.get(priorite, 1.0)
    
    prix_total *= mult_type * mult_prio
    
    # Remises volume
    if poids > 1000:
        prix_total *= 0.95  # 5% de remise
    elif poids > 500:
        prix_total *= 0.97  # 3% de remise
    
    # Ajout des frais annexes
    cout_carburant = estimer_cout_carburant(distance)
    peages = estimer_peages(distance)
    
    prix_final = prix_total + cout_carburant + peages
    
    return {
        'prix_base': round(prix_total, 2),
        'carburant': cout_carburant,
        'peages': peages,
        'total': round(prix_final, 2)
    }

# ==========================================
# DONNÉES MÉTÉO ET TRAFIC (SIMULATION)
# ==========================================

def obtenir_conditions_meteo(ville):
    """Simuler les conditions météo actuelles"""
    conditions = ['ensoleille', 'nuageux', 'pluie', 'brouillard']
    condition = random.choice(conditions)
    
    # Simulation réaliste selon la saison
    mois = timezone.now().month
    
    if mois in [12, 1, 2]:  # Hiver
        temperature = random.randint(8, 18)
        if random.random() < 0.3:
            condition = 'pluie'
    elif mois in [6, 7, 8]:  # Été
        temperature = random.randint(25, 40)
        condition = random.choice(['ensoleille', 'ensoleille', 'nuageux'])
    else:
        temperature = random.randint(15, 28)
    
    return {
        'ville': ville,
        'temperature': temperature,
        'condition': condition,
        'vent_km_h': random.randint(5, 25),
        'visibilite_km': 10 if condition != 'brouillard' else random.randint(1, 5),
        'alerte': condition in ['pluie', 'brouillard'],
        'recommandation': get_recommandation_meteo(condition)
    }

def get_recommandation_meteo(condition):
    """Obtenir une recommandation selon la météo"""
    recommandations = {
        'pluie': 'Réduire la vitesse, augmenter les distances de sécurité',
        'brouillard': 'Conduite très prudente, utiliser feux de brouillard',
        'ensoleille': 'Conditions optimales pour la conduite',
        'nuageux': 'Conditions normales de conduite'
    }
    return recommandations.get(condition, 'Conditions normales')

def obtenir_conditions_trafic(zone, heure=None):
    """Simuler les conditions de trafic"""
    if not heure:
        heure = timezone.now().hour
    
    # Simulation réaliste selon l'heure
    if 7 <= heure <= 9 or 17 <= heure <= 19:  # Heures de pointe
        niveau = random.choice(['dense', 'normal', 'dense'])
    elif 22 <= heure or heure <= 6:  # Nuit
        niveau = 'fluide'
    else:
        niveau = random.choice(['fluide', 'normal'])
    
    vitesses = {
        'fluide': 80,
        'normal': 60,
        'dense': 40,
        'bloque': 20
    }
    
    return {
        'zone': zone,
        'niveau': niveau,
        'vitesse_moyenne': vitesses[niveau],
        'retard_estime': 0 if niveau == 'fluide' else 10 if niveau == 'normal' else 30,
        'heure_maj': timezone.now(),
        'recommandation': get_recommandation_trafic(niveau)
    }

def get_recommandation_trafic(niveau):
    """Obtenir une recommandation selon le trafic"""
    recommandations = {
        'fluide': 'Circulation normale',
        'normal': 'Quelques ralentissements possibles',
        'dense': 'Prévoir du temps supplémentaire',
        'bloque': 'Éviter cette zone si possible'
    }
    return recommandations.get(niveau, 'Conditions normales')

# ==========================================
# UTILITAIRES DE VALIDATION
# ==========================================

def valider_coordonnees(latitude, longitude):
    """Valider des coordonnées GPS"""
    try:
        lat = float(latitude)
        lng = float(longitude)
        
        # Vérifier les plages
        if not (-90 <= lat <= 90):
            return False, "Latitude invalide"
        
        if not (-180 <= lng <= 180):
            return False, "Longitude invalide"
        
        # Vérifier si c'est au Maroc (approximatif)
        if not (27 <= lat <= 36 and -17 <= lng <= 2):
            return False, "Coordonnées hors Maroc"
        
        return True, "Coordonnées valides"
        
    except (ValueError, TypeError):
        return False, "Format invalide"

def formater_duree(minutes):
    """Formater une durée en minutes vers format lisible"""
    if minutes < 60:
        return f"{int(minutes)} min"
    
    heures = int(minutes // 60)
    mins = int(minutes % 60)
    
    if mins == 0:
        return f"{heures}h"
    else:
        return f"{heures}h {mins}min"

def formater_distance(distance_km):
    """Formater une distance"""
    if distance_km < 1:
        return f"{int(distance_km * 1000)} m"
    else:
        return f"{distance_km:.1f} km"

# ==========================================
# CACHE ET PERFORMANCE
# ==========================================

def get_cached_or_calculate(cache_key, calculation_func, timeout=3600, *args, **kwargs):
    """Obtenir une valeur du cache ou la calculer"""
    result = cache.get(cache_key)
    
    if result is None:
        try:
            result = calculation_func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
        except Exception as e:
            logger.error(f"Erreur calcul {cache_key}: {e}")
            result = None
    
    return result

def clear_cache_pattern(pattern):
    """Nettoyer le cache selon un pattern"""
    # Implementation dépendante du backend de cache
    # Pour Redis: utiliser KEYS pattern et DELETE
    # Pour LocMem: pas de pattern matching natif
    pass

# ==========================================
# HELPERS POUR LES TEMPLATES
# ==========================================

def get_status_color(statut):
    """Obtenir la couleur pour un statut"""
    colors = {
        'EN_ATTENTE': '#ffc107',     # Jaune
        'AFFECTEE': '#17a2b8',       # Bleu clair
        'EN_TRANSIT': '#007bff',     # Bleu
        'LIVREE': '#28a745',         # Vert
        'ANNULEE': '#dc3545'         # Rouge
    }
    return colors.get(statut, '#6c757d')

def get_priority_badge(priorite):
    """Obtenir le badge pour une priorité"""
    badges = {
        0: {'text': 'Normale', 'class': 'badge-secondary'},
        1: {'text': 'Haute', 'class': 'badge-warning'},
        2: {'text': 'Urgente', 'class': 'badge-danger'}
    }
    return badges.get(priorite, badges[0])