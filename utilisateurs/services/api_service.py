import requests
import math
from django.conf import settings

class TransportAPIService:
    
    @staticmethod
    def geocode_address(address):
        """Convertir une adresse en coordonnées GPS"""
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{address}, Morocco",
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data:
                return {
                    'lat': float(data[0]['lat']),
                    'lng': float(data[0]['lon']),
                    'display_name': data[0]['display_name'],
                    'city': data[0].get('address', {}).get('city', ''),
                    'country': data[0].get('address', {}).get('country', '')
                }
        except Exception as e:
            print(f"Erreur géocodage: {e}")
        
        return None
    
    @staticmethod
    def calculate_route_openroute(origin_coords, dest_coords):
        """Calculer itinéraire avec OpenRouteService"""
        if not settings.OPENROUTE_API_KEY:
            return None
            
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {
            'Authorization': f'Bearer {settings.OPENROUTE_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # OpenRouteService utilise [longitude, latitude]
        coordinates = [
            [origin_coords['lng'], origin_coords['lat']],
            [dest_coords['lng'], dest_coords['lat']]
        ]
        
        data = {
            "coordinates": coordinates,
            "format": "json",
            "instructions": "true",
            "language": "fr"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=15)
            
            if response.status_code == 200:
                route_data = response.json()
                route = route_data['routes'][0]
                
                return {
                    'distance_km': round(route['summary']['distance'] / 1000, 2),
                    'duration_hours': round(route['summary']['duration'] / 3600, 2),
                    'duration_minutes': round(route['summary']['duration'] / 60),
                    'geometry': route['geometry'],  # Pour afficher sur carte
                    'instructions': route.get('segments', [{}])[0].get('steps', [])
                }
            else:
                print(f"Erreur OpenRoute: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Erreur calcul route: {e}")
        
        return None
    
    @staticmethod
    def calculate_distance_duration(origin, destination):
        """Calculer distance et durée entre deux adresses"""
        # Géocoder les adresses
        origin_coords = TransportAPIService.geocode_address(origin)
        dest_coords = TransportAPIService.geocode_address(destination)
        
        if not origin_coords or not dest_coords:
            return None
        
        # Essayer d'abord avec OpenRouteService
        route_info = TransportAPIService.calculate_route_openroute(origin_coords, dest_coords)
        
        if route_info:
            route_info.update({
                'origin_coords': origin_coords,
                'dest_coords': dest_coords
            })
            return route_info
        
        # Fallback: calcul simple avec formule haversine
        lat1, lng1 = math.radians(origin_coords['lat']), math.radians(origin_coords['lng'])
        lat2, lng2 = math.radians(dest_coords['lat']), math.radians(dest_coords['lng'])
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = 6371 * c  # Rayon de la Terre en km
        
        # Estimation durée (vitesse moyenne 60 km/h)
        duration = distance / 60
        
        return {
            'distance_km': round(distance, 2),
            'duration_hours': round(duration, 2),
            'duration_minutes': round(duration * 60),
            'origin_coords': origin_coords,
            'dest_coords': dest_coords,
            'method': 'haversine_fallback'
        }
    
    @staticmethod
    def get_weather_info(city="Casablanca"):
        """Obtenir informations météo"""
        if not settings.OPENWEATHER_API_KEY:
            return None
            
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': f"{city},MA",
            'appid': settings.OPENWEATHER_API_KEY,
            'units': 'metric',
            'lang': 'fr'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'city': data['name'],
                    'temperature': round(data['main']['temp']),
                    'feels_like': round(data['main']['feels_like']),
                    'description': data['weather'][0]['description'].title(),
                    'icon': data['weather'][0]['icon'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': round(data['wind']['speed'] * 3.6, 1),  # Convert m/s to km/h
                    'visibility': data.get('visibility', 0) / 1000 if data.get('visibility') else None
                }
            else:
                print(f"Erreur Weather API: {response.status_code}")
                
        except Exception as e:
            print(f"Erreur météo: {e}")
        
        return None
    
    @staticmethod
    def get_route_geometry_points(geometry_string):
        """Décoder la géométrie pour affichage sur carte"""
        try:
            # OpenRouteService renvoie un polyline encodé
            # Vous pouvez utiliser une librairie comme polyline pour le décoder
            # Pour l'instant, retournons une liste vide
            return []
        except Exception as e:
            print(f"Erreur décodage géométrie: {e}")
            return []
