# utilisateurs/services/google_maps_service.py

import googlemaps
import requests
from django.conf import settings
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class GoogleMapsService:
    """Service dédié pour Google Maps API"""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.client = googlemaps.Client(key=self.api_key) if self.api_key else None
    
    def geocode_address(self, address: str) -> Optional[Dict]:
        """Géocoder une adresse"""
        if not self.client:
            return None
            
        try:
            result = self.client.geocode(address)
            if result:
                location = result[0]['geometry']['location']
                return {
                    'lat': location['lat'],
                    'lng': location['lng'],
                    'formatted_address': result[0]['formatted_address']
                }
        except Exception as e:
            logger.error(f"Erreur géocodage: {e}")
        return None
    
    def calculate_route(self, origin: str, destination: str, waypoints: List[str] = None) -> Optional[Dict]:
        """Calculer un itinéraire optimisé"""
        if not self.client:
            return None
            
        try:
            result = self.client.directions(
                origin=origin,
                destination=destination,
                waypoints=waypoints,
                optimize_waypoints=True,
                mode="driving"
            )
            
            if result:
                route = result[0]
                return {
                    'distance': route['legs'][0]['distance']['text'],
                    'duration': route['legs'][0]['duration']['text'],
                    'polyline': route['overview_polyline']['points'],
                    'waypoint_order': route.get('waypoint_order', [])
                }
        except Exception as e:
            logger.error(f"Erreur calcul itinéraire: {e}")
        return None
    
    def optimize_delivery_route(self, depot: str, deliveries: List[str]) -> Optional[Dict]:
        """Optimiser une tournée de livraison"""
        if not self.client or not deliveries:
            return None
            
        try:
            # Utiliser l'API Directions avec optimisation des waypoints
            result = self.client.directions(
                origin=depot,
                destination=depot,
                waypoints=deliveries,
                optimize_waypoints=True,
                mode="driving"
            )
            
            if result:
                route = result[0]
                total_distance = sum(leg['distance']['value'] for leg in route['legs'])
                total_duration = sum(leg['duration']['value'] for leg in route['legs'])
                
                return {
                    'optimized_order': route.get('waypoint_order', []),
                    'total_distance_km': round(total_distance / 1000, 2),
                    'total_duration_min': round(total_duration / 60, 2),
                    'polyline': route['overview_polyline']['points'],
                    'legs': route['legs']
                }
        except Exception as e:
            logger.error(f"Erreur optimisation tournée: {e}")
        return None