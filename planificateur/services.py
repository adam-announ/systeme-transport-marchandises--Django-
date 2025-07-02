"""
Services pour l'optimisation et la planification
"""

import requests
import json
from django.conf import settings
from typing import Dict, List, Tuple

class OptimisationService:
    """Service d'optimisation d'itinéraires"""
    
    def __init__(self):
        self.google_api_key = settings.GOOGLE_MAPS_API_KEY
        self.openroute_api_key = settings.OPENROUTE_API_KEY
    
    def optimiser_itineraire(self, lat_depart: float, lng_depart: float, 
                           lat_arrivee: float, lng_arrivee: float, 
                           conditions_meteo: Dict = None) -> Dict:
        """Optimise un itinéraire entre deux points"""
        
        # Tentative avec Google Maps API
        if self.google_api_key:
            try:
                return self._optimiser_avec_google(lat_depart, lng_depart, lat_arrivee, lng_arrivee)
            except Exception as e:
                print(f"Erreur Google Maps: {e}")
        
        # Fallback avec OpenRoute Service
        if self.openroute_api_key:
            try:
                return self._optimiser_avec_openroute(lat_depart, lng_depart, lat_arrivee, lng_arrivee)
            except Exception as e:
                print(f"Erreur OpenRoute: {e}")
        
        # Fallback avec calcul basique
        return self._calcul_basique(lat_depart, lng_depart, lat_arrivee, lng_arrivee)
    
    def _optimiser_avec_google(self, lat_depart: float, lng_depart: float, 
                              lat_arrivee: float, lng_arrivee: float) -> Dict:
        """Optimisation avec Google Maps Directions API"""
        
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            'origin': f"{lat_depart},{lng_depart}",
            'destination': f"{lat_arrivee},{lng_arrivee}",
            'key': self.google_api_key,
            'optimize': 'true',
            'language': 'fr',
            'units': 'metric'
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            route = data['routes'][0]
            leg = route['legs'][0]
            
            return {
                'distance': leg['distance']['value'] / 1000,  # en km
                'duree': leg['duration']['value'] / 60,  # en minutes
                'points': self._decode_polyline(route['overview_polyline']['points']),
                'instructions': [step['html_instructions'] for step in leg['steps']]
            }
        
        raise Exception(f"Erreur Google Maps: {data['status']}")
    
    def _optimiser_avec_openroute(self, lat_depart: float, lng_depart: float, 
                                 lat_arrivee: float, lng_arrivee: float) -> Dict:
        """Optimisation avec OpenRoute Service"""
        
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {
            'Authorization': self.openroute_api_key,
            'Content-Type': 'application/json'
        }
        
        body = {
            'coordinates': [[lng_depart, lat_depart], [lng_arrivee, lat_arrivee]],
            'format': 'json',
            'instructions': True,
            'language': 'fr'
        }
        
        response = requests.post(url, json=body, headers=headers)
        data = response.json()
        
        if 'routes' in data:
            route = data['routes'][0]
            summary = route['summary']
            
            return {
                'distance': summary['distance'] / 1000,  # en km
                'duree': summary['duration'] / 60,  # en minutes
                'points': route['geometry']['coordinates'],
                'instructions': [step['instruction'] for step in route['segments'][0]['steps']]
            }
        
        raise Exception("Erreur OpenRoute Service")
    
    def _calcul_basique(self, lat_depart: float, lng_depart: float, 
                       lat_arrivee: float, lng_arrivee: float) -> Dict:
        """Calcul basique de distance (fallback)"""
        
        # Calcul de distance à vol d'oiseau (formule de Haversine)
        import math
        
        R = 6371  # Rayon de la Terre en km
        
        lat1_rad = math.radians(lat_depart)
        lat2_rad = math.radians(lat_arrivee)
        delta_lat = math.radians(lat_arrivee - lat_depart)
        delta_lng = math.radians(lng_arrivee - lng_depart)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lng/2) * math.sin(delta_lng/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        # Estimation du temps (vitesse moyenne 50 km/h)
        duree = (distance / 50) * 60  # en minutes
        
        return {
            'distance': distance * 1.3,  # Facteur de correction pour routes
            'duree': duree,
            'points': [[lng_depart, lat_depart], [lng_arrivee, lat_arrivee]],
            'instructions': ['Suivre l\'itinéraire optimal']
        }
    
    def _decode_polyline(self, polyline_str: str) -> List[List[float]]:
        """Décode une polyline Google Maps"""
        index = 0
        lat = 0
        lng = 0
        coordinates = []
        
        while index < len(polyline_str):
            # Décodage latitude
            result = 1
            shift = 0
            while True:
                b = ord(polyline_str[index]) - 63 - 1
                index += 1
                result += b << shift
                shift += 5
                if b < 0x1f:
                    break
            lat += (~result >> 1) if (result & 1) != 0 else (result >> 1)
            
            # Décodage longitude
            result = 1
            shift = 0
            while True:
                b = ord(polyline_str[index]) - 63 - 1
                index += 1
                result += b << shift
                shift += 5
                if b < 0x1f:
                    break
            lng += (~result >> 1) if (result & 1) != 0 else (result >> 1)
            
            coordinates.append([lng / 1e5, lat / 1e5])
        
        return coordinates

class MeteoService:
    """Service météorologique"""
    
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
    
    def get_weather(self, lat: float, lng: float) -> Dict:
        """Récupère les conditions météorologiques"""
        
        if not self.api_key:
            return {'condition': 'inconnue', 'temperature': 20}
        
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': lat,
                'lon': lng,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'fr'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            return {
                'condition': data['weather'][0]['description'],
                'temperature': data['main']['temp'],
                'humidite': data['main']['humidity'],
                'vent': data['wind']['speed'],
                'visibilite': data.get('visibility', 10000) / 1000  # en km
            }
            
        except Exception as e:
            print(f"Erreur météo: {e}")
            return {'condition': 'inconnue', 'temperature': 20}

class PlanificationService:
    """Service de planification des tournées"""
    
    def planifier_tournee(self, commandes: List, transporteur_id: str) -> Dict:
        """Planifie une tournée optimale pour plusieurs commandes"""
        
        if not commandes:
            return {'success': False, 'message': 'Aucune commande à planifier'}
        
        # Tri des commandes par proximité géographique
        commandes_triees = self._trier_par_proximite(commandes)
        
        # Calcul de l'itinéraire global
        itineraire_global = self._calculer_itineraire_global(commandes_triees)
        
        return {
            'success': True,
            'commandes_ordre': [str(c.id) for c in commandes_triees],
            'distance_totale': itineraire_global['distance_totale'],
            'duree_totale': itineraire_global['duree_totale'],
            'points_passage': itineraire_global['points']
        }
    
    def _trier_par_proximite(self, commandes: List) -> List:
        """Trie les commandes par proximité géographique (algorithme du plus proche voisin)"""
        if len(commandes) <= 1:
            return commandes
        
        commandes_triees = [commandes[0]]
        commandes_restantes = commandes[1:]
        
        while commandes_restantes:
            derniere_commande = commandes_triees[-1]
            plus_proche = min(commandes_restantes, 
                            key=lambda c: self._distance_euclidienne(
                                derniere_commande.latitude_livraison,
                                derniere_commande.longitude_livraison,
                                c.latitude_enlevement,
                                c.longitude_enlevement
                            ))
            commandes_triees.append(plus_proche)
            commandes_restantes.remove(plus_proche)
        
        return commandes_triees
    
    def _distance_euclidienne(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calcule la distance euclidienne entre deux points"""
        import math
        return math.sqrt((lat2 - lat1)**2 + (lng2 - lng1)**2)
    
    def _calculer_itineraire_global(self, commandes: List) -> Dict:
        """Calcule l'itinéraire global pour une tournée"""
        distance_totale = 0
        duree_totale = 0
        points = []
        
        for i, commande in enumerate(commandes):
            # Point d'enlèvement
            points.append([commande.longitude_enlevement, commande.latitude_enlevement])
            
            # Distance enlèvement -> livraison
            service = OptimisationService()
            itineraire = service.optimiser_itineraire(
                commande.latitude_enlevement,
                commande.longitude_enlevement,
                commande.latitude_livraison,
                commande.longitude_livraison
            )
            
            distance_totale += itineraire['distance']
            duree_totale += itineraire['duree']
            
            # Point de livraison
            points.append([commande.longitude_livraison, commande.latitude_livraison])
            
            # Distance vers la prochaine commande
            if i < len(commandes) - 1:
                prochaine_commande = commandes[i + 1]
                itineraire_suivant = service.optimiser_itineraire(
                    commande.latitude_livraison,
                    commande.longitude_livraison,
                    prochaine_commande.latitude_enlevement,
                    prochaine_commande.longitude_enlevement
                )
                distance_totale += itineraire_suivant['distance']
                duree_totale += itineraire_suivant['duree']
        
        return {
            'distance_totale': distance_totale,
            'duree_totale': duree_totale,
            'points': points
        }