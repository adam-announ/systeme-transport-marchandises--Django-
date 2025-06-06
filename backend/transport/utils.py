# backend/transport/utils.py - Version complète avec toutes les fonctions
import math
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

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
    try:
        if hasattr(commande, 'itineraire') and commande.itineraire.distance_km:
            prix += Decimal(str(commande.itineraire.distance_km)) * tarif_distance
    except:
        # Si pas d'itinéraire, estimation basée sur les villes
        pass
    
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
    """Optimiser un itinéraire"""
    # Version simplifiée sans Google Maps
    # En production, vous pouvez ajouter l'intégration Google Maps
    
    try:
        # Calcul estimé basé sur les villes
        origine = f"{commande.adresse_enlevement.ville}, {commande.adresse_enlevement.pays}"
        destination = f"{commande.adresse_livraison.ville}, {commande.adresse_livraison.pays}"
        
        # Distance estimée (formule simplifiée)
        # En réalité, utiliser une API de géolocalisation
        if (commande.adresse_enlevement.latitude and commande.adresse_enlevement.longitude and
            commande.adresse_livraison.latitude and commande.adresse_livraison.longitude):
            
            distance = calculer_distance_haversine(
                commande.adresse_enlevement.latitude,
                commande.adresse_enlevement.longitude,
                commande.adresse_livraison.latitude,
                commande.adresse_livraison.longitude
            )
        else:
            # Distance par défaut basée sur les noms de villes
            distance = 50.0  # km par défaut
        
        # Durée estimée (vitesse moyenne de 60 km/h)
        duree = (distance / 60) * 60  # en minutes
        
        return {
            'distance_km': round(distance, 2),
            'duree_minutes': int(duree),
            'polyline': '',
            'instructions': [],
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
    from .models import Transporteur  # Import local pour éviter les imports circulaires
    
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
    from .models import Notification  # Import local pour éviter les imports circulaires
    
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
    from .models import Commande  # Import local
    
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
    # Version simplifiée sans Google Maps API
    # En production, vous pouvez ajouter l'intégration Google Maps
    
    try:
        # Coordonnées par défaut pour les principales villes du Maroc
        villes_coordonnees = {
            'casablanca': {'lat': 33.5731, 'lng': -7.5898},
            'rabat': {'lat': 34.0209, 'lng': -6.8416},
            'marrakech': {'lat': 31.6295, 'lng': -7.9811},
            'fès': {'lat': 34.0331, 'lng': -5.0003},
            'tanger': {'lat': 35.7595, 'lng': -5.8340},
            'agadir': {'lat': 30.4278, 'lng': -9.5981},
            'meknes': {'lat': 33.8935, 'lng': -5.5473},
            'oujda': {'lat': 34.6867, 'lng': -1.9114},
            'kenitra': {'lat': 34.2610, 'lng': -6.5802},
            'tetouan': {'lat': 35.5889, 'lng': -5.3626}
        }
        
        ville = adresse_data.get('ville', '').lower()
        for ville_ref, coords in villes_coordonnees.items():
            if ville_ref in ville:
                adresse_data['latitude'] = coords['lat']
                adresse_data['longitude'] = coords['lng']
                break
    
    except Exception as e:
        print(f"Erreur lors de la validation d'adresse: {e}")
    
    return adresse_data

def calculer_estimation_livraison(commande):
    """Calculer l'estimation de livraison"""
    try:
        # Facteurs de calcul
        distance_base = 50  # km par défaut
        vitesse_moyenne = 60  # km/h
        temps_preparation = 2  # heures
        
        # Si on a un itinéraire calculé
        if hasattr(commande, 'itineraire') and commande.itineraire:
            distance = commande.itineraire.distance_km or distance_base
        else:
            distance = distance_base
        
        # Temps de transport
        temps_transport = distance / vitesse_moyenne
        
        # Temps total
        temps_total = temps_preparation + temps_transport
        
        # Ajouter selon la priorité
        if commande.priorite == 'urgente':
            temps_total *= 0.7  # Réduction de 30%
        elif commande.priorite == 'haute':
            temps_total *= 0.85  # Réduction de 15%
        elif commande.priorite == 'basse':
            temps_total *= 1.2   # Augmentation de 20%
        
        # Date estimée
        from datetime import timedelta
        date_estimation = timezone.now() + timedelta(hours=temps_total)
        
        return date_estimation
        
    except Exception as e:
        print(f"Erreur lors du calcul d'estimation: {e}")
        return None

def verifier_capacite_transporteur(transporteur, commande):
    """Vérifier si un transporteur peut prendre une commande"""
    # Vérifier la capacité de charge
    if commande.poids > transporteur.capacite_charge:
        return False, "Poids supérieur à la capacité du véhicule"
    
    # Vérifier la capacité de volume si spécifiée
    if commande.volume and transporteur.capacite_volume:
        if commande.volume > transporteur.capacite_volume:
            return False, "Volume supérieur à la capacité du véhicule"
    
    # Vérifier la disponibilité
    if not transporteur.disponibilite:
        return False, "Transporteur non disponible"
    
    # Vérifier le nombre de missions actives
    missions_actives = transporteur.commandes.filter(
        statut__in=['assignee', 'en_transit', 'en_cours_livraison']
    ).count()
    
    if missions_actives >= 3:  # Limite de 3 missions simultanées
        return False, "Transporteur a trop de missions actives"
    
    return True, "Transporteur compatible"

def mettre_a_jour_position_transporteur(transporteur, latitude, longitude):
    """Mettre à jour la position d'un transporteur"""
    try:
        transporteur.position_latitude = latitude
        transporteur.position_longitude = longitude
        transporteur.derniere_position_update = timezone.now()
        transporteur.save()
        
        return True
    except Exception as e:
        print(f"Erreur lors de la mise à jour de position: {e}")
        return False

def calculer_itineraire_simple(origine, destination):
    """Calculer un itinéraire simple entre deux points"""
    try:
        # Version simplifiée - en production utiliser une vraie API
        distance_estimee = 50.0  # km par défaut
        duree_estimee = 60  # minutes par défaut
        
        return {
            'distance_km': distance_estimee,
            'duree_minutes': duree_estimee,
            'polyline': '',
            'instructions': [
                f"Partir de {origine}",
                f"Se diriger vers {destination}",
                f"Arrivée à {destination}"
            ]
        }
    except Exception as e:
        print(f"Erreur lors du calcul d'itinéraire: {e}")
        return None

def envoyer_email_notification(notification):
    """Envoyer une notification par email (optionnel)"""
    try:
        from django.core.mail import send_mail
        
        subject = notification.titre
        message = notification.message
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [notification.destinataire.email]
        
        send_mail(subject, message, from_email, recipient_list, fail_silently=True)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi d'email: {e}")
        return False

def envoyer_sms_notification(notification, numero_telephone):
    """Envoyer une notification par SMS (optionnel)"""
    try:
        # Ici vous pouvez intégrer un service SMS comme Twilio
        # Pour l'instant, juste un log
        print(f"SMS envoyé à {numero_telephone}: {notification.message}")
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de SMS: {e}")
        return False

def log_action_utilisateur(utilisateur, action, details=""):
    """Enregistrer une action utilisateur dans le journal"""
    from .models import Journal  # Import local
    
    try:
        Journal.objects.create(
            utilisateur=utilisateur,
            action=action,
            description=details,
            adresse_ip=getattr(utilisateur, 'ip_address', None),
            user_agent=getattr(utilisateur, 'user_agent', '')
        )
        return True
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du journal: {e}")
        return False