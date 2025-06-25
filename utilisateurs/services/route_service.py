import requests
from django.conf import settings
from typing import List, Dict, Tuple
import json

class RouteOptimizationService:
    def __init__(self):
        self.api_key = settings.OPENROUTE_API_KEY
        self.base_url = "https://api.openrouteservice.org"
    
    def geocode_address(self, address: str) -> Tuple[float, float]:
        """Convertit une adresse en coordonnées lat/lng"""
        url = f"{self.base_url}/geocode/search"
        params = {
            'api_key': self.api_key,
            'text': address,
            'size': 1
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['features']:
                    coords = data['features'][0]['geometry']['coordinates']
                    return coords[1], coords[0]  # lat, lng
        except Exception as e:
            print(f"Erreur géocodage: {e}")
        
        return None, None
    
    def optimize_route(self, locations: List[Dict]) -> Dict:
        """Optimise un itinéraire avec plusieurs points"""
        if len(locations) < 2:
            return {'error': 'Au moins 2 points requis'}
        
        # Préparer les coordonnées
        coordinates = []
        for loc in locations:
            lat, lng = self.geocode_address(loc['address'])
            if lat and lng:
                coordinates.append([lng, lat])  # OpenRoute utilise lng, lat
        
        if len(coordinates) < 2:
            return {'error': 'Impossible de géocoder les adresses'}
        
        # Optimisation TSP (Traveling Salesman Problem)
        url = f"{self.base_url}/optimization"
        
        payload = {
            "jobs": [
                {
                    "id": i,
                    "location": coord,
                    "service": 300  # 5 minutes par arrêt
                }
                for i, coord in enumerate(coordinates[1:], 1)  # Exclure le point de départ
            ],
            "vehicles": [
                {
                    "id": 1,
                    "start": coordinates[0],
                    "end": coordinates[0],
                    "capacity": [1000]
                }
            ]
        }
        
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return self._process_optimization_result(response.json(), locations)
        except Exception as e:
            print(f"Erreur optimisation: {e}")
        
        # Fallback: ordre simple
        return self._simple_route_calculation(locations)
    
    def _process_optimization_result(self, result: Dict, locations: List[Dict]) -> Dict:
        """Traite le résultat de l'optimisation"""
        if 'routes' not in result or not result['routes']:
            return self._simple_route_calculation(locations)
        
        route = result['routes'][0]
        steps = route['steps']
        
        optimized_order = []
        total_distance = 0
        total_time = 0
        
        for step in steps:
            if step['type'] == 'job':
                job_id = step['job']
                location = locations[job_id]
                optimized_order.append({
                    'id': location['id'],
                    'address': location['address'],
                    'order': len(optimized_order) + 1
                })
            
            total_distance += step.get('distance', 0)
            total_time += step.get('duration', 0)
        
        return {
            'optimized_order': optimized_order,
            'total_distance': round(total_distance / 1000, 2),  # en km
            'total_time': round(total_time / 3600, 2),  # en heures
            'success': True
        }
    
    def _simple_route_calculation(self, locations: List[Dict]) -> Dict:
        """Calcul simple sans optimisation"""
        return {
            'optimized_order': [
                {
                    'id': loc['id'],
                    'address': loc['address'],
                    'order': i + 1
                }
                for i, loc in enumerate(locations[1:])  # Exclure le dépôt
            ],
            'total_distance': len(locations) * 15,  # Estimation
            'total_time': len(locations) * 0.5,  # Estimation
            'success': True,
            'fallback': True
        }