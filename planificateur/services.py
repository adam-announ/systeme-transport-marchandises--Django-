"""
Services améliorés avec APIs réelles pour l'optimisation et la planification
"""

import requests
import json
import googlemaps
from django.conf import settings
from typing import Dict, List, Tuple, Optional
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import math
from datetime import datetime, timedelta
from core.models import ConfigurationSysteme

class GeocodingService:
    """Service de géocodage avec plusieurs APIs"""
    
    def __init__(self):
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        self.gmaps_client = None
        if self.google_api_key:
            self.gmaps_client = googlemaps.Client(key=self.google_api_key)
        
        self.nominatim = Nominatim(user_agent="transport_system_2024")
    
    def geocoder_adresse(self, adresse: str) -> Optional[Dict]:
        """Géocode une adresse avec fallback"""
        
        # Tentative avec Google Maps Geocoding API
        if self.gmaps_client:
            try:
                result = self.gmaps_client.geocode(adresse)
                if result:
                    location = result[0]['geometry']['location']
                    return {
                        'latitude': location['lat'],
                        'longitude': location['lng'],
                        'adresse_formatee': result[0]['formatted_address'],
                        'composants': result[0]['address_components'],
                        'source': 'google'
                    }
            except Exception as e:
                print(f"Erreur Google Geocoding: {e}")
        
        # Fallback avec Nominatim (OpenStreetMap)
        try:
            location = self.nominatim.geocode(adresse, timeout=10)
            if location:
                return {
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'adresse_formatee': location.address,
                    'source': 'nominatim'
                }
        except Exception as e:
            print(f"Erreur Nominatim: {e}")
        
        return None
    
    def reverse_geocoder(self, lat: float, lng: float) -> Optional[Dict]:
        """Géocodage inverse"""
        
        if self.gmaps_client:
            try:
                result = self.gmaps_client.reverse_geocode((lat, lng))
                if result:
                    return {
                        'adresse': result[0]['formatted_address'],
                        'composants': result[0]['address_components'],
                        'source': 'google'
                    }
            except Exception as e:
                print(f"Erreur Google Reverse Geocoding: {e}")
        
        try:
            location = self.nominatim.reverse((lat, lng), timeout=10)
            if location:
                return {
                    'adresse': location.address,
                    'source': 'nominatim'
                }
        except Exception as e:
            print(f"Erreur Nominatim Reverse: {e}")
        
        return None

class OptimisationService:
    """Service d'optimisation d'itinéraires avec APIs réelles"""
    
    def __init__(self):
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        self.openroute_api_key = getattr(settings, 'OPENROUTE_API_KEY', '')
        self.gmaps_client = None
        
        if self.google_api_key:
            self.gmaps_client = googlemaps.Client(key=self.google_api_key)
    
    def optimiser_itineraire(self, lat_depart: float, lng_depart: float, 
                           lat_arrivee: float, lng_arrivee: float, 
                           waypoints: List[Tuple[float, float]] = None,
                           vehicle_type: str = 'truck',
                           avoid_tolls: bool = False,
                           avoid_highways: bool = False) -> Dict:
        """Optimise un itinéraire entre deux points avec waypoints optionnels"""
        
        # Tentative avec Google Maps Directions API
        if self.gmaps_client:
            try:
                return self._optimiser_avec_google(
                    lat_depart, lng_depart, lat_arrivee, lng_arrivee,
                    waypoints, avoid_tolls, avoid_highways
                )
            except Exception as e:
                print(f"Erreur Google Maps: {e}")
        
        # Fallback avec OpenRoute Service
        if self.openroute_api_key:
            try:
                return self._optimiser_avec_openroute(
                    lat_depart, lng_depart, lat_arrivee, lng_arrivee,
                    waypoints, vehicle_type
                )
            except Exception as e:
                print(f"Erreur OpenRoute: {e}")
        
        # Fallback avec calcul basique
        return self._calcul_basique(lat_depart, lng_depart, lat_arrivee, lng_arrivee)
    
    def _optimiser_avec_google(self, lat_depart: float, lng_depart: float, 
                              lat_arrivee: float, lng_arrivee: float,
                              waypoints: List[Tuple[float, float]] = None,
                              avoid_tolls: bool = False,
                              avoid_highways: bool = False) -> Dict:
        """Optimisation avec Google Maps Directions API"""
        
        origin = f"{lat_depart},{lng_depart}"
        destination = f"{lat_arrivee},{lng_arrivee}"
        
        # Préparation des waypoints
        waypoints_str = None
        if waypoints:
            waypoints_str = '|'.join([f"{lat},{lng}" for lat, lng in waypoints])
        
        # Évitements
        avoid = []
        if avoid_tolls:
            avoid.append('tolls')
        if avoid_highways:
            avoid.append('highways')
        
        params = {
            'origin': origin,
            'destination': destination,
            'mode': 'driving',
            'optimize': True,
            'language': 'fr',
            'units': 'metric',
            'traffic_model': 'best_guess',
            'departure_time': datetime.now()
        }
        
        if waypoints_str:
            params['waypoints'] = f"optimize:true|{waypoints_str}"
        
        if avoid:
            params['avoid'] = '|'.join(avoid)
        
        try:
            result = self.gmaps_client.directions(**params)
            
            if result:
                route = result[0]
                leg = route['legs'][0] if len(route['legs']) == 1 else route['legs']
                
                # Calcul des totaux pour plusieurs legs
                total_distance = sum(leg['distance']['value'] for leg in route['legs']) / 1000
                total_duration = sum(leg['duration']['value'] for leg in route['legs']) / 60
                
                # Instructions détaillées
                instructions = []
                for leg in route['legs']:
                    for step in leg['steps']:
                        instructions.append({
                            'instruction': step['html_instructions'],
                            'distance': step['distance']['text'],
                            'duration': step['duration']['text'],
                            'start_location': step['start_location'],
                            'end_location': step['end_location']
                        })
                
                return {
                    'distance': total_distance,
                    'duree': total_duration,
                    'points': self._decode_polyline(route['overview_polyline']['points']),
                    'polyline': route['overview_polyline']['points'],
                    'instructions': instructions,
                    'trafic_info': self._extraire_info_trafic(route),
                    'cout_peage': self._calculer_cout_peage(route),
                    'source': 'google'
                }
        
        except Exception as e:
            raise Exception(f"Erreur Google Maps: {e}")
    
    def _optimiser_avec_openroute(self, lat_depart: float, lng_depart: float, 
                                 lat_arrivee: float, lng_arrivee: float,
                                 waypoints: List[Tuple[float, float]] = None,
                                 vehicle_type: str = 'truck') -> Dict:
        """Optimisation avec OpenRoute Service"""
        
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        if vehicle_type == 'truck':
            url = "https://api.openrouteservice.org/v2/directions/driving-hgv"
        
        headers = {
            'Authorization': self.openroute_api_key,
            'Content-Type': 'application/json'
        }
        
        coordinates = [[lng_depart, lat_depart]]
        if waypoints:
            coordinates.extend([[lng, lat] for lat, lng in waypoints])
        coordinates.append([lng_arrivee, lat_arrivee])
        
        body = {
            'coordinates': coordinates,
            'format': 'json',
            'instructions': True,
            'language': 'fr',
            'geometry': True,
            'elevation': True
        }
        
        response = requests.post(url, json=body, headers=headers)
        data = response.json()
        
        if 'routes' in data:
            route = data['routes'][0]
            summary = route['summary']
            
            instructions = []
            for segment in route['segments']:
                for step in segment['steps']:
                    instructions.append({
                        'instruction': step['instruction'],
                        'distance': f"{step['distance']/1000:.1f} km",
                        'duration': f"{step['duration']/60:.0f} min"
                    })
            
            return {
                'distance': summary['distance'] / 1000,
                'duree': summary['duration'] / 60,
                'points': route['geometry']['coordinates'],
                'instructions': instructions,
                'elevation_gain': route.get('elevation', {}).get('ascent', 0),
                'source': 'openroute'
            }
        
        raise Exception("Erreur OpenRoute Service")
    
    def _calcul_basique(self, lat_depart: float, lng_depart: float, 
                       lat_arrivee: float, lng_arrivee: float) -> Dict:
        """Calcul basique de distance avec géopy"""
        
        point_depart = (lat_depart, lng_depart)
        point_arrivee = (lat_arrivee, lng_arrivee)
        
        # Distance géodésique précise
        distance = geodesic(point_depart, point_arrivee).kilometers
        
        # Estimation du temps basée sur le type de route
        vitesse_moyenne = 60  # km/h en ville/route
        if distance > 100:  # Autoroute probable
            vitesse_moyenne = 90
        
        duree = (distance / vitesse_moyenne) * 60  # en minutes
        
        return {
            'distance': distance * 1.2,  # Facteur de correction pour routes
            'duree': duree,
            'points': [[lng_depart, lat_depart], [lng_arrivee, lat_arrivee]],
            'instructions': [
                {'instruction': f'Partir de {lat_depart:.4f}, {lng_depart:.4f}'},
                {'instruction': f'Arriver à {lat_arrivee:.4f}, {lng_arrivee:.4f}'}
            ],
            'source': 'calcul_basique'
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
    
    def _extraire_info_trafic(self, route: Dict) -> Dict:
        """Extrait les informations de trafic"""
        trafic_info = {
            'duration_in_traffic': 0,
            'traffic_conditions': 'unknown'
        }
        
        for leg in route['legs']:
            if 'duration_in_traffic' in leg:
                trafic_info['duration_in_traffic'] += leg['duration_in_traffic']['value']
        
        # Comparaison avec durée normale
        duree_normale = sum(leg['duration']['value'] for leg in route['legs'])
        if trafic_info['duration_in_traffic'] > 0:
            ratio = trafic_info['duration_in_traffic'] / duree_normale
            if ratio > 1.5:
                trafic_info['traffic_conditions'] = 'heavy'
            elif ratio > 1.2:
                trafic_info['traffic_conditions'] = 'moderate'
            else:
                trafic_info['traffic_conditions'] = 'light'
        
        return trafic_info
    
    def _calculer_cout_peage(self, route: Dict) -> float:
        """Calcule le coût estimé des péages"""
        # Estimation basique basée sur la distance
        distance_totale = sum(leg['distance']['value'] for leg in route['legs']) / 1000
        cout_peage = 0
        
        # Estimation: 0.08€/km sur autoroute (à ajuster selon le pays)
        if distance_totale > 50:  # Probable usage autoroute
            cout_peage = distance_totale * 0.08
        
        return cout_peage

class MeteoService:
    """Service météorologique avec API réelle"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENWEATHER_API_KEY', '')
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    def get_weather_current(self, lat: float, lng: float) -> Dict:
        """Récupère les conditions météorologiques actuelles"""
        
        if not self.api_key:
            return self._weather_fallback()
        
        try:
            url = f"{self.base_url}/weather"
            params = {
                'lat': lat,
                'lon': lng,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'fr'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'temperature': data['main']['temp'],
                'temperature_ressentie': data['main']['feels_like'],
                'humidite': data['main']['humidity'],
                'pression': data['main']['pressure'],
                'description': data['weather'][0]['description'],
                'icone': data['weather'][0]['icon'],
                'vent_vitesse': data['wind']['speed'],
                'vent_direction': data['wind'].get('deg', 0),
                'visibilite': data.get('visibility', 10000) / 1000,
                'nuages': data['clouds']['all'],
                'lever_soleil': datetime.fromtimestamp(data['sys']['sunrise']),
                'coucher_soleil': datetime.fromtimestamp(data['sys']['sunset']),
                'conditions_conduite': self._evaluer_conditions_conduite(data),
                'source': 'openweather'
            }
            
        except Exception as e:
            print(f"Erreur météo: {e}")
            return self._weather_fallback()
    
    def get_weather_forecast(self, lat: float, lng: float, days: int = 5) -> List[Dict]:
        """Récupère les prévisions météorologiques"""
        
        if not self.api_key:
            return [self._weather_fallback() for _ in range(days)]
        
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': lat,
                'lon': lng,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'fr'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            forecasts = []
            for item in data['list'][:days * 8]:  # 8 prévisions par jour (3h)
                forecasts.append({
                    'date': datetime.fromtimestamp(item['dt']),
                    'temperature': item['main']['temp'],
                    'description': item['weather'][0]['description'],
                    'icone': item['weather'][0]['icon'],
                    'probabilite_pluie': item.get('pop', 0) * 100,
                    'vent_vitesse': item['wind']['speed'],
                    'conditions_conduite': self._evaluer_conditions_conduite(item)
                })
            
            return forecasts
            
        except Exception as e:
            print(f"Erreur prévisions météo: {e}")
            return [self._weather_fallback() for _ in range(days)]
    
    def _evaluer_conditions_conduite(self, weather_data: Dict) -> Dict:
        """Évalue les conditions de conduite basées sur la météo"""
        
        conditions = {
            'score': 100,  # Score sur 100
            'niveau': 'excellent',
            'recommandations': []
        }
        
        # Analyse de la pluie
        if 'rain' in weather_data:
            rain_volume = weather_data['rain'].get('1h', 0)
            if rain_volume > 10:
                conditions['score'] -= 30
                conditions['recommandations'].append("Pluie forte - Réduire la vitesse")
            elif rain_volume > 2:
                conditions['score'] -= 15
                conditions['recommandations'].append("Pluie modérée - Prudence")
        
        # Analyse du vent
        wind_speed = weather_data['wind']['speed']
        if wind_speed > 15:  # > 54 km/h
            conditions['score'] -= 25
            conditions['recommandations'].append("Vent fort - Attention aux véhicules légers")
        elif wind_speed > 10:  # > 36 km/h
            conditions['score'] -= 10
            conditions['recommandations'].append("Vent modéré")
        
        # Analyse de la visibilité
        visibility = weather_data.get('visibility', 10000)
        if visibility < 1000:
            conditions['score'] -= 40
            conditions['recommandations'].append("Visibilité réduite - Allumer les feux")
        elif visibility < 5000:
            conditions['score'] -= 20
            conditions['recommandations'].append("Visibilité limitée")
        
        # Analyse de la neige/verglas
        if 'snow' in weather_data:
            conditions['score'] -= 50
            conditions['recommandations'].append("Neige - Équipements spéciaux requis")
        
        # Détermination du niveau
        if conditions['score'] >= 80:
            conditions['niveau'] = 'excellent'
        elif conditions['score'] >= 60:
            conditions['niveau'] = 'bon'
        elif conditions['score'] >= 40:
            conditions['niveau'] = 'moyen'
        else:
            conditions['niveau'] = 'difficile'
        
        return conditions
    
    def _weather_fallback(self) -> Dict:
        """Données météo par défaut"""
        return {
            'temperature': 20,
            'description': 'Conditions inconnues',
            'humidite': 50,
            'vent_vitesse': 5,
            'visibilite': 10,
            'conditions_conduite': {
                'score': 75,
                'niveau': 'bon',
                'recommandations': ['Données météo non disponibles']
            },
            'source': 'fallback'
        }

class TrafficService:
    """Service d'information trafic"""
    
    def __init__(self):
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        self.gmaps_client = None
        
        if self.google_api_key:
            self.gmaps_client = googlemaps.Client(key=self.google_api_key)
    
    def get_traffic_info(self, lat_depart: float, lng_depart: float,
                        lat_arrivee: float, lng_arrivee: float) -> Dict:
        """Récupère les informations de trafic en temps réel"""
        
        if not self.gmaps_client:
            return self._traffic_fallback()
        
        try:
            # Directions avec info trafic
            result = self.gmaps_client.directions(
                origin=f"{lat_depart},{lng_depart}",
                destination=f"{lat_arrivee},{lng_arrivee}",
                mode="driving",
                departure_time=datetime.now(),
                traffic_model="best_guess"
            )
            
            if result:
                route = result[0]
                leg = route['legs'][0]
                
                duration_normal = leg['duration']['value']
                duration_traffic = leg.get('duration_in_traffic', {}).get('value', duration_normal)
                
                delay_minutes = (duration_traffic - duration_normal) / 60
                
                traffic_level = 'light'
                if delay_minutes > 30:
                    traffic_level = 'heavy'
                elif delay_minutes > 10:
                    traffic_level = 'moderate'
                
                return {
                    'duree_normale': duration_normal / 60,
                    'duree_avec_trafic': duration_traffic / 60,
                    'retard_minutes': delay_minutes,
                    'niveau_trafic': traffic_level,
                    'recommandation': self._get_traffic_recommendation(traffic_level),
                    'mise_a_jour': datetime.now(),
                    'source': 'google'
                }
                
        except Exception as e:
            print(f"Erreur info trafic: {e}")
        
        return self._traffic_fallback()
    
    def _get_traffic_recommendation(self, traffic_level: str) -> str:
        """Retourne une recommandation basée sur le niveau de trafic"""
        recommendations = {
            'light': 'Conditions de circulation normales',
            'moderate': 'Trafic modéré - Prévoir 15-30 minutes supplémentaires',
            'heavy': 'Trafic dense - Envisager un itinéraire alternatif ou reporter'
        }
        return recommendations.get(traffic_level, 'Conditions inconnues')
    
    def _traffic_fallback(self) -> Dict:
        """Données trafic par défaut"""
        return {
            'niveau_trafic': 'unknown',
            'recommandation': 'Informations trafic non disponibles',
            'retard_minutes': 0,
            'source': 'fallback'
        }

class PlanificationService:
    """Service de planification des tournées amélioré"""
    
    def __init__(self):
        self.optimisation_service = OptimisationService()
        self.meteo_service = MeteoService()
        self.traffic_service = TrafficService()
    
    def planifier_tournee_optimale(self, commandes: List, transporteur_id: str,
                                  vehicule_id: str = None) -> Dict:
        """Planifie une tournée optimale avec algorithme génétique simplifié"""
        
        if not commandes:
            return {'success': False, 'message': 'Aucune commande à planifier'}
        
        # Optimisation de l'ordre des commandes
        commandes_optimisees = self._optimiser_ordre_commandes(commandes)
        
        # Calcul de l'itinéraire global
        itineraire_global = self._calculer_itineraire_tournee(commandes_optimisees)
        
        # Analyse des conditions
        conditions = self._analyser_conditions_tournee(commandes_optimisees)
        
        # Estimation des coûts
        estimation_couts = self._estimer_couts_tournee(itineraire_global, vehicule_id)
        
        return {
            'success': True,
            'commandes_ordre': [str(c.id) for c in commandes_optimisees],
            'itineraire': itineraire_global,
            'conditions': conditions,
            'estimation_couts': estimation_couts,
            'recommandations': self._generer_recommandations(conditions),
            'score_optimisation': self._calculer_score_optimisation(commandes_optimisees, itineraire_global)
        }
    
    def _optimiser_ordre_commandes(self, commandes: List) -> List:
        """Optimise l'ordre des commandes avec algorithme du plus proche voisin amélioré"""
        
        if len(commandes) <= 1:
            return commandes
        
        # Matrice des distances
        distances = self._calculer_matrice_distances(commandes)
        
        # Algorithme du plus proche voisin avec optimisation 2-opt
        commandes_triees = self._plus_proche_voisin(commandes, distances)
        commandes_optimisees = self._optimisation_2opt(commandes_triees, distances)
        
        return commandes_optimisees
    
    def _calculer_matrice_distances(self, commandes: List) -> Dict:
        """Calcule la matrice des distances entre toutes les commandes"""
        
        distances = {}
        for i, cmd1 in enumerate(commandes):
            for j, cmd2 in enumerate(commandes):
                if i != j:
                    key = f"{i}-{j}"
                    # Distance de livraison de cmd1 à enlèvement de cmd2
                    point1 = (cmd1.adresse_livraison.latitude, cmd1.adresse_livraison.longitude)
                    point2 = (cmd2.adresse_enlevement.latitude, cmd2.adresse_enlevement.longitude)
                    distances[key] = geodesic(point1, point2).kilometers
        
        return distances
    
    def _plus_proche_voisin(self, commandes: List, distances: Dict) -> List:
        """Implémente l'algorithme du plus proche voisin"""
        
        if not commandes:
            return []
        
        commandes_triees = [commandes[0]]
        commandes_restantes = commandes[1:]
        
        while commandes_restantes:
            derniere_index = commandes.index(commandes_triees[-1])
            
            plus_proche = min(
                commandes_restantes,
                key=lambda c: distances.get(f"{derniere_index}-{commandes.index(c)}", float('inf'))
            )
            
            commandes_triees.append(plus_proche)
            commandes_restantes.remove(plus_proche)
        
        return commandes_triees
    
    def _optimisation_2opt(self, commandes: List, distances: Dict) -> List:
        """Optimisation 2-opt pour améliorer la tournée"""
        
        if len(commandes) < 4:
            return commandes
        
        meilleure_tournee = commandes[:]
        meilleure_distance = self._calculer_distance_totale(commandes, distances)
        
        amelioration = True
        iterations = 0
        max_iterations = min(50, len(commandes) * 2)
        
        while amelioration and iterations < max_iterations:
            amelioration = False
            iterations += 1
            
            for i in range(1, len(commandes) - 2):
                for j in range(i + 1, len(commandes)):
                    if j - i == 1:
                        continue
                    
                    nouvelle_tournee = self._inverser_segment(commandes, i, j)
                    nouvelle_distance = self._calculer_distance_totale(nouvelle_tournee, distances)
                    
                    if nouvelle_distance < meilleure_distance:
                        meilleure_tournee = nouvelle_tournee
                        meilleure_distance = nouvelle_distance
                        commandes = nouvelle_tournee[:]
                        amelioration = True
        
        return meilleure_tournee
    
    def _inverser_segment(self, tournee: List, i: int, j: int) -> List:
        """Inverse un segment de la tournée"""
        nouvelle_tournee = tournee[:]
        nouvelle_tournee[i:j] = reversed(nouvelle_tournee[i:j])
        return nouvelle_tournee
    
    def _calculer_distance_totale(self, commandes: List, distances: Dict) -> float:
        """Calcule la distance totale d'une tournée"""
        
        distance_totale = 0
        
        for i in range(len(commandes)):
            # Distance enlèvement -> livraison pour chaque commande
            point1 = (commandes[i].adresse_enlevement.latitude, commandes[i].adresse_enlevement.longitude)
            point2 = (commandes[i].adresse_livraison.latitude, commandes[i].adresse_livraison.longitude)
            distance_totale += geodesic(point1, point2).kilometers
            
            # Distance vers la prochaine commande
            if i < len(commandes) - 1:
                key = f"{i}-{i+1}"
                distance_totale += distances.get(key, 0)
        
        return distance_totale
    
    def _calculer_itineraire_tournee(self, commandes: List) -> Dict:
        """Calcule l'itinéraire complet de la tournée"""
        
        distance_totale = 0
        duree_totale = 0
        points_tournee = []
        instructions_tournee = []
        
        for i, commande in enumerate(commandes):
            # Itinéraire enlèvement -> livraison
            itineraire = self.optimisation_service.optimiser_itineraire(
                commande.adresse_enlevement.latitude,
                commande.adresse_enlevement.longitude,
                commande.adresse_livraison.latitude,
                commande.adresse_livraison.longitude
            )
            
            distance_totale += itineraire['distance']
            duree_totale += itineraire['duree']
            points_tournee.extend(itineraire['points'])
            
            instructions_tournee.append({
                'type': 'enlevement',
                'commande': commande.numero,
                'adresse': commande.adresse_enlevement.adresse_complete,
                'instructions': f"Enlèvement - {commande.description_marchandise}"
            })
            
            instructions_tournee.append({
                'type': 'livraison',
                'commande': commande.numero,
                'adresse': commande.adresse_livraison.adresse_complete,
                'instructions': f"Livraison - {commande.description_marchandise}"
            })
            
            # Distance vers la prochaine commande
            if i < len(commandes) - 1:
                prochaine_commande = commandes[i + 1]
                itineraire_suivant = self.optimisation_service.optimiser_itineraire(
                    commande.adresse_livraison.latitude,
                    commande.adresse_livraison.longitude,
                    prochaine_commande.adresse_enlevement.latitude,
                    prochaine_commande.adresse_enlevement.longitude
                )
                distance_totale += itineraire_suivant['distance']
                duree_totale += itineraire_suivant['duree']
        
        return {
            'distance_totale': distance_totale,
            'duree_totale': duree_totale,
            'nombre_arrets': len(commandes) * 2,
            'points': points_tournee,
            'instructions': instructions_tournee
        }
    
    def _analyser_conditions_tournee(self, commandes: List) -> Dict:
        """Analyse les conditions météo et trafic pour la tournée"""
        
        conditions = {
            'meteo': [],
            'trafic': [],
            'score_global': 0,
            'risques': []
        }
        
        # Analyse météo pour chaque point
        for commande in commandes:
            meteo_enlevement = self.meteo_service.get_weather_current(
                commande.adresse_enlevement.latitude,
                commande.adresse_enlevement.longitude
            )
            
            conditions['meteo'].append({
                'commande': commande.numero,
                'type': 'enlevement',
                'conditions': meteo_enlevement
            })
        
        # Score global basé sur les conditions
        conditions['score_global'] = min([m['conditions']['conditions_conduite']['score'] 
                                        for m in conditions['meteo']])
        
        return conditions
    
    def _estimer_couts_tournee(self, itineraire: Dict, vehicule_id: str = None) -> Dict:
        """Estime les coûts de la tournée"""
        
        # Paramètres par défaut
        cout_carburant_km = 0.15  # €/km
        cout_main_oeuvre_heure = 25  # €/h
        cout_peages = 0.08  # €/km sur autoroute
        
        # Récupération depuis la configuration
        try:
            config_carburant = ConfigurationSysteme.objects.get(cle='cout_carburant_km')
            cout_carburant_km = float(config_carburant.valeur)
        except:
            pass
        
        distance = itineraire['distance_totale']
        duree_heures = itineraire['duree_totale'] / 60
        
        couts = {
            'carburant': distance * cout_carburant_km,
            'main_oeuvre': duree_heures * cout_main_oeuvre_heure,
            'peages': distance * cout_peages * 0.3,  # 30% de routes à péage estimé
            'total': 0
        }
        
        couts['total'] = sum(couts.values())
        
        return couts
    
    def _generer_recommandations(self, conditions: Dict) -> List[str]:
        """Génère des recommandations pour la tournée"""
        
        recommandations = []
        
        if conditions['score_global'] < 60:
            recommandations.append("Conditions météo difficiles - Prévoir plus de temps")
        
        if conditions['score_global'] < 40:
            recommandations.append("Conditions dangereuses - Envisager de reporter")
        
        # Ajout d'autres recommandations basées sur l'analyse
        recommandations.append("Vérifier l'état du véhicule avant départ")
        recommandations.append("Prévoir des équipements de sécurité")
        
        return recommandations
    
    def _calculer_score_optimisation(self, commandes: List, itineraire: Dict) -> int:
        """Calcule un score d'optimisation de la tournée"""
        
        # Score basé sur l'efficacité de la tournée
        nombre_commandes = len(commandes)
        distance_moyenne_par_commande = itineraire['distance_totale'] / nombre_commandes
        
        # Score de 0 à 100
        if distance_moyenne_par_commande < 10:
            return 95
        elif distance_moyenne_par_commande < 20:
            return 85
        elif distance_moyenne_par_commande < 50:
            return 70
        else:
            return 50