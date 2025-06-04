# transport/utils.py
import googlemaps
import math
from decimal import Decimal
from django.conf import settings
from .models import Commande, Transporteur, Itineraire

def calculer_prix(commande):
    """Calculer le prix estimé d'une commande"""
    if not commande.poids:
        return None
    
    # Tarifs de base
    tarif_base = Decimal('50.00')  # Coût de base
    tarif_poids = Decimal('2.00')  # Par kg
    tarif_distance = Decimal('1.50')  # Par km
    
    # Calcul du prix de base
    prix = tarif_base + (Decimal(str(commande.poids)) * tarif_poids)
    
    # Ajouter le coût de distance si disponible
    if hasattr(commande, 'itineraire') and commande.itineraire.distance_km:
        prix += Decimal(str(commande.itineraire.distance_km)) * tarif_distance
    
    # Multiplicateur selon la priorité
    multiplicateurs = {
        'basse': Decimal('0.9'),
        'normale': Decimal('1.0'),
        'haute': Decimal('1.2'),
        'urgente': Decimal('1.5')
    }
    
    multiplicateur = multiplicateurs.get(commande.priorite, Decimal('1.0'))
    prix = prix * multiplicateur
    
    # Majoration selon le type de marchandise
    majorations = {
        'fragile': Decimal('1.1'),
        'dangereux': Decimal('1.3'),
        'chimique': Decimal('1.2')
    }
    
    majoration = majorations.get(commande.type_marchandise, Decimal('1.0'))
    prix = prix * majoration
    
    return round(prix, 2)

def optimiser_itineraire(commande):
    """Optimiser un itinéraire avec Google Maps"""
    if not settings.GOOGLE_MAPS_API_KEY:
        return None
    
    try:
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        
        origine = f"{commande.adresse_enlevement.rue}, {commande.adresse_enlevement.ville}, {commande.adresse_enlevement.pays}"
        destination = f"{commande.adresse_livraison.rue}, {commande.adresse_livraison.ville}, {commande.adresse_livraison.pays}"
        
        # Calculer les directions
        directions = gmaps.directions(
            origin=origine,
            destination=destination,
            mode="driving",
            optimize_waypoints=True,
            language='fr'
        )
        
        if directions:
            route = directions[0]
            leg = route['legs'][0]
            
            return {
                'distance_km': leg['distance']['value'] / 1000,
                'duree_minutes': leg['duration']['value'] / 60,
                'polyline': route['overview_polyline']['points'],
                'instructions': [step['html_instructions'] for step in leg['steps']],
                'optimise': True
            }
    
    except Exception as e:
        print(f"Erreur lors de l'optimisation: {e}")
    
    return None

def calculer_distance_haversine(lat1, lon1, lat2, lon2):
    """Calculer la distance entre deux points géographiques"""
    R = 6371  # Rayon de la Terre en km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance

def trouver_transporteur_optimal(commande):
    """Trouver le meilleur transporteur pour une commande"""
    transporteurs_disponibles = Transporteur.objects.filter(
        disponibilite=True,
        statut='disponible',
        capacite_charge__gte=commande.poids
    )
    
    if not transporteurs_disponibles.exists():
        return None
    
    # Calculer le score pour chaque transporteur
    meilleur_transporteur = None
    meilleur_score = float('inf')
    
    for transporteur in transporteurs_disponibles:
        score = calculer_score_transporteur(transporteur, commande)
        if score < meilleur_score:
            meilleur_score = score
            meilleur_transporteur = transporteur
    
    return meilleur_transporteur

def calculer_score_transporteur(transporteur, commande):
    """Calculer un score pour un transporteur (plus bas = meilleur)"""
    score = 0
    
    # Distance (si position connue)
    if (transporteur.position_latitude and transporteur.position_longitude and
        commande.adresse_enlevement.latitude and commande.adresse_enlevement.longitude):
        
        distance = calculer_distance_haversine(
            transporteur.position_latitude, transporteur.position_longitude,
            commande.adresse_enlevement.latitude, commande.adresse_enlevement.longitude
        )
        score += distance * 10  # Pénalité de distance
    
    # Capacité (préférer les capacités adaptées)
    ratio_capacite = commande.poids / transporteur.capacite_charge
    if ratio_capacite > 0.8:
        score += 50  # Pénalité pour surcharge
    elif ratio_capacite < 0.3:
        score += 20  # Pénalité pour sous-utilisation
    
    # Rating du transporteur (inverser pour que meilleur rating = score plus bas)
    score += (5 - transporteur.rating) * 10
    
    # Nombre de missions actives
    missions_actives = transporteur.commandes.filter(
        statut__in=['assignee', 'en_transit', 'en_cours_livraison']
    ).count()
    score += missions_actives * 15
    
    return score

def envoyer_notification(destinataire, type_notification, titre, message, commande=None):
    """Créer une notification pour un utilisateur"""
    from .models import Notification
    
    try:
        notification = Notification.objects.create(
            destinataire=destinataire,
            type_notification=type_notification,
            titre=titre,
            message=message,
            commande=commande
        )
        
        # Ici, vous pourriez ajouter l'envoi par email, SMS, ou push notification
        # envoyer_email_notification(notification)
        # envoyer_push_notification(notification)
        
        return notification
    except Exception as e:
        print(f"Erreur lors de l'envoi de notification: {e}")
        return None

def generer_numero_commande():
    """Générer un numéro de commande unique"""
    from datetime import datetime
    from .models import Commande
    
    today = datetime.now()
    prefix = f"CMD{today.strftime('%Y%m%d')}"
    
    # Trouver le dernier numéro du jour
    last_command = Commande.objects.filter(
        numero__startswith=prefix
    ).order_by('-numero').first()
    
    if last_command:
        try:
            last_number = int(last_command.numero[-4:])
            new_number = last_number + 1
        except ValueError:
            new_number = 1
    else:
        new_number = 1
    
    return f"{prefix}{new_number:04d}"

def valider_adresse(adresse_data):
    """Valider et géocoder une adresse"""
    if not settings.GOOGLE_MAPS_API_KEY:
        return adresse_data
    
    try:
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        
        adresse_complete = f"{adresse_data.get('rue', '')}, {adresse_data.get('ville', '')}, {adresse_data.get('pays', '')}"
        
        geocode_result = gmaps.geocode(adresse_complete, language='fr')
        
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            adresse_data['latitude'] = location['lat']
            adresse_data['longitude'] = location['lng']
            
            # Améliorer l'adresse avec les données de Google
            components = geocode_result[0]['address_components']
            formatted_address = geocode_result[0]['formatted_address']
            
            for component in components:
                types = component['types']
                if 'postal_code' in types:
                    adresse_data['code_postal'] = component['long_name']
                elif 'locality' in types:
                    adresse_data['ville'] = component['long_name']
                elif 'country' in types:
                    adresse_data['pays'] = component['long_name']
    
    except Exception as e:
        print(f"Erreur lors de la validation d'adresse: {e}")
    
    return adresse_data