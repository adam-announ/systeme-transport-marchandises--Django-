# utilisateurs/services/geoapify_service.py

import requests
from django.conf import settings
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class GeoapifyService:
    """Service pour Geoapify API - Alternative performante à Google Maps"""
    
    def __init__(self):
        self.api_key = settings.GEOAPIFY_API_KEY
        self.base_url = "https://api.geoapify.com"
    
    def geocode_address(self, address: str) -> Optional[Dict]:
        """Géocoder une adresse"""
        if not self.api_key:
            return None
            
        try:
            url = f"{self.base_url}/v1/geocode/search"
            params = {
                'text': address,
                'apiKey': self.api_key,
                'limit': 1,
                'filter': 'countrycode:ma'  # Limiter au Maroc
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('features') and len(data['features']) > 0:
                feature = data['features'][0]
                coords = feature['geometry']['coordinates']
                
                return {
                    'lat': coords[1],
                    'lng': coords[0],
                    'formatted_address': feature['properties'].get('formatted', address),
                    'city': feature['properties'].get('city', ''),
                    'country': feature['properties'].get('country', 'Morocco')
                }
        except Exception as e:
            logger.error(f"Erreur géocodage Geoapify: {e}")
        return None
    
    def calculate_route(self, waypoints: List[Dict]) -> Optional[Dict]:
        """Calculer un itinéraire optimisé"""
        if not self.api_key or len(waypoints) < 2:
            return None
            
        try:
            # Préparer les coordonnées
            coordinates = []
            for point in waypoints:
                if 'lat' in point and 'lng' in point:
                    coordinates.append([point['lng'], point['lat']])
            
            if len(coordinates) < 2:
                return None
            
            url = f"{self.base_url}/v1/routing"
            params = {
                'waypoints': '|'.join([f"{coord[1]},{coord[0]}" for coord in coordinates]),
                'mode': 'drive',
                'apiKey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if data.get('features') and len(data['features']) > 0:
                route = data['features'][0]
                properties = route['properties']
                
                return {
                    'distance_km': round(properties['distance'] / 1000, 2),
                    'duration_minutes': round(properties['time'] / 60),
                    'geometry': route['geometry'],
                    'success': True,
                    'source': 'geoapify'
                }
        except Exception as e:
            logger.error(f"Erreur calcul itinéraire Geoapify: {e}")
        return None
    
    def optimize_route(self, depot: Dict, deliveries: List[Dict]) -> Optional[Dict]:
        """Optimiser une tournée de livraison"""
        if not self.api_key or not deliveries:
            return None
            
        try:
            # Préparer les points
            locations = [depot] + deliveries
            coordinates = []
            
            for loc in locations:
                if 'lat' in loc and 'lng' in loc:
                    coordinates.append([loc['lng'], loc['lat']])
            
            if len(coordinates) < 2:
                return None
            
            url = f"{self.base_url}/v1/routeplanner"
            params = {
                'waypoints': '|'.join([f"{coord[1]},{coord[0]}" for coord in coordinates]),
                'mode': 'drive',
                'apiKey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            
            data = response.json()
            if data.get('features') and len(data['features']) > 0:
                route = data['features'][0]
                properties = route['properties']
                
                return {
                    'total_distance_km': round(properties['distance'] / 1000, 2),
                    'total_duration_minutes': round(properties['time'] / 60),
                    'waypoint_order': properties.get('waypoint_order', []),
                    'geometry': route['geometry'],
                    'success': True,
                    'source': 'geoapify'
                }
        except Exception as e:
            logger.error(f"Erreur optimisation Geoapify: {e}")
        return None