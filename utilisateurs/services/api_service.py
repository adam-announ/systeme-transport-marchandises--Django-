# utilisateurs/services/api_service.py

import requests
import json
from decimal import Decimal
from django.conf import settings
from typing import Dict, List, Optional, Tuple
import logging
import time

logger = logging.getLogger(__name__)

class TransportAPIService:
    """Service pour intégrer les APIs externes (OpenWeather et OpenRoute)"""
    
    OPENROUTE_BASE_URL = "https://api.openrouteservice.org"
    OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    @staticmethod
    def geocode_address(address: str) -> Optional[Tuple[float, float]]:
        """Géocode une adresse avec OpenRoute Service"""
        try:
            api_key = settings.OPENROUTE_API_KEY
            if not api_key:
                logger.warning("Clé API OpenRoute manquante")
                return None
            
            url = f"{TransportAPIService.OPENROUTE_BASE_URL}/geocode/search"
            params = {
                'api_key': api_key,
                'text': address,
                'size': 1,
                'boundary.country': 'MA'  # Limiter au Maroc
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('features') and len(data['features']) > 0:
                coordinates = data['features'][0]['geometry']['coordinates']
                # OpenRoute retourne [longitude, latitude]
                return coordinates[1], coordinates[0]  # Retourner [latitude, longitude]
            
            return None
            
        except requests.RequestException as e:
            logger.error(f"Erreur géocodage OpenRoute: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue géocodage: {e}")
            return None

    @staticmethod
    def calculate_distance_duration(origine: str, destination: str) -> Optional[Dict]:
        """Calcule la distance et durée entre deux points avec OpenRoute Service"""
        try:
            # Géocoder les adresses
            coord_origine = TransportAPIService.geocode_address(origine)
            coord_destination = TransportAPIService.geocode_address(destination)
            
            if not coord_origine or not coord_destination:
                logger.warning(f"Impossible de géocoder: {origine} -> {destination}")
                return TransportAPIService._fallback_calculation(origine, destination)
            
            # Calculer l'itinéraire
            api_key = settings.OPENROUTE_API_KEY
            url = f"{TransportAPIService.OPENROUTE_BASE_URL}/v2/directions/driving-car"
            
            headers = {
                'Authorization': api_key,
                'Content-Type': 'application/json'
            }
            
            body = {
                "coordinates": [
                    [coord_origine[1], coord_origine[0]],  # [longitude, latitude]
                    [coord_destination[1], coord_destination[0]]
                ],
                "format": "json",
                "units": "km"
            }
            
            response = requests.post(url, headers=headers, json=body, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('routes') and len(data['routes']) > 0:
                route = data['routes'][0]['summary']
                distance_km = round(route['distance'] / 1000, 2)  # Convertir en km
                duration_seconds = route['duration']
                duration_hours = round(duration_seconds / 3600, 2)
                
                return {
                    'distance_km': distance_km,
                    'duration_hours': duration_hours,
                    'duration_minutes': round(duration_seconds / 60),
                    'duration_seconds': duration_seconds,
                    'origine_coords': coord_origine,
                    'destination_coords': coord_destination,
                    'success': True,
                    'source': 'openroute'
                }
            
            return TransportAPIService._fallback_calculation(origine, destination)
            
        except requests.RequestException as e:
            logger.error(f"Erreur API OpenRoute: {e}")
            return TransportAPIService._fallback_calculation(origine, destination)
        except Exception as e:
            logger.error(f"Erreur calcul distance: {e}")
            return TransportAPIService._fallback_calculation(origine, destination)

    @staticmethod
    def get_route_optimization(points: List[Dict]) -> Optional[Dict]:
        """Optimise un itinéraire avec plusieurs points"""
        try:
            if len(points) < 2:
                return None
            
            api_key = settings.OPENROUTE_API_KEY
            url = f"{TransportAPIService.OPENROUTE_BASE_URL}/optimization"
            
            headers = {
                'Authorization': api_key,
                'Content-Type': 'application/json'
            }
            
            # Préparer les coordonnées
            coordinates = []
            for point in points:
                if 'latitude' in point and 'longitude' in point:
                    coordinates.append([point['longitude'], point['latitude']])
                elif 'address' in point:
                    coords = TransportAPIService.geocode_address(point['address'])
                    if coords:
                        coordinates.append([coords[1], coords[0]])  # [longitude, latitude]
            
            if len(coordinates) < 2:
                return None
            
            # Créer les jobs (points de livraison)
            jobs = []
            for i, coord in enumerate(coordinates[1:], 1):  # Exclure le dépôt
                jobs.append({
                    "id": i,
                    "location": coord,
                    "service": 1800  # 30 minutes de service par défaut
                })
            
            # Véhicule
            vehicles = [{
                "id": 1,
                "start": coordinates[0],  # Dépôt
                "end": coordinates[0],    # Retour au dépôt
                "profile": "driving-car"
            }]
            
            body = {
                "jobs": jobs,
                "vehicles": vehicles
            }
            
            response = requests.post(url, headers=headers, json=body, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'routes' in data and len(data['routes']) > 0:
                route = data['routes'][0]
                
                return {
                    'optimized_sequence': [step.get('job', 0) for step in route['steps'] if step['type'] == 'job'],
                    'total_distance': round(route['distance'] / 1000, 2),  # km
                    'total_duration': round(route['duration'] / 3600, 2),  # heures
                    'total_service_time': round(route['service'] / 3600, 2),  # heures
                    'steps': route['steps'],
                    'success': True,
                    'source': 'openroute'
                }
            
            return None
            
        except requests.RequestException as e:
            logger.error(f"Erreur optimisation OpenRoute: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur optimisation: {e}")
            return None

    @staticmethod
    def get_weather_info(city: str) -> Optional[Dict]:
        """Récupère les informations météo avec OpenWeather API"""
        try:
            api_key = settings.OPENWEATHER_API_KEY
            if not api_key:
                logger.warning("Clé API OpenWeather manquante")
                return None
            
            url = f"{TransportAPIService.OPENWEATHER_BASE_URL}/weather"
            params = {
                'q': f"{city},MA",  # Maroc
                'appid': api_key,
                'units': 'metric',
                'lang': 'fr'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'temperature': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'wind_speed': data.get('wind', {}).get('speed', 0),
                'visibility': data.get('visibility', 10000) / 1000,  # km
                'conditions': data['weather'][0]['main'],
                'icon': data['weather'][0]['icon'],
                'success': True
            }
            
        except requests.RequestException as e:
            logger.error(f"Erreur API OpenWeather: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur météo: {e}")
            return None

    @staticmethod
    def get_weather_forecast(city: str, days: int = 5) -> Optional[List[Dict]]:
        """Récupère les prévisions météo"""
        try:
            api_key = settings.OPENWEATHER_API_KEY
            if not api_key:
                return None
            
            url = f"{TransportAPIService.OPENWEATHER_BASE_URL}/forecast"
            params = {
                'q': f"{city},MA",
                'appid': api_key,
                'units': 'metric',
                'lang': 'fr',
                'cnt': days * 8  # 8 prévisions par jour (toutes les 3h)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            forecasts = []
            for item in data['list']:
                forecasts.append({
                    'datetime': item['dt_txt'],
                    'temperature': item['main']['temp'],
                    'humidity': item['main']['humidity'],
                    'description': item['weather'][0]['description'],
                    'wind_speed': item.get('wind', {}).get('speed', 0),
                    'conditions': item['weather'][0]['main'],
                    'icon': item['weather'][0]['icon']
                })
            
            return forecasts
            
        except requests.RequestException as e:
            logger.error(f"Erreur prévisions météo: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur prévisions: {e}")
            return None

    @staticmethod
    def check_weather_conditions_for_transport(city: str) -> Dict:
        """Vérifie si les conditions météo sont favorables au transport"""
        weather = TransportAPIService.get_weather_info(city)
        
        if not weather:
            return {
                'suitable': True,
                'warnings': [],
                'score': 8,  # Score par défaut
                'message': 'Informations météo non disponibles'
            }
        
        warnings = []
        score = 10
        
        # Vérifications des conditions
        if weather['conditions'].lower() in ['rain', 'drizzle', 'thunderstorm']:
            warnings.append('Conditions pluvieuses - Prudence recommandée')
            score -= 2
        
        if weather['conditions'].lower() in ['snow', 'mist', 'fog']:
            warnings.append('Visibilité réduite - Retards possibles')
            score -= 3
        
        if weather['wind_speed'] > 15:  # m/s
            warnings.append('Vents forts - Attention aux véhicules légers')
            score -= 1
        
        if weather['temperature'] < 0:
            warnings.append('Risque de verglas')
            score -= 2
        
        if weather['temperature'] > 45:
            warnings.append('Chaleur extrême - Précautions nécessaires')
            score -= 1
        
        suitable = score >= 6
        
        if suitable and not warnings:
            message = 'Conditions météo favorables au transport'
        elif suitable:
            message = 'Transport possible avec précautions'
        else:
            message = 'Conditions météo défavorables - Report recommandé'
        
        return {
            'suitable': suitable,
            'warnings': warnings,
            'score': score,
            'message': message,
            'weather_data': weather
        }

    @staticmethod
    def _fallback_calculation(origine: str, destination: str) -> Dict:
        """Calcul de distance approximatif en cas d'échec de l'API"""
        # Distances approximatives entre les principales villes du Maroc
        distances_matrix = {
            ('casablanca', 'rabat'): 87,
            ('casablanca', 'marrakech'): 241,
            ('casablanca', 'fes'): 296,
            ('casablanca', 'tanger'): 338,
            ('rabat', 'marrakech'): 327,
            ('rabat', 'fes'): 209,
            ('rabat', 'tanger'): 251,
            ('marrakech', 'fes'): 537,
            ('marrakech', 'tanger'): 579,
            ('fes', 'tanger'): 289,
        }
        
        # Normaliser les noms de villes
        origine_norm = TransportAPIService._normalize_city_name(origine)
        destination_norm = TransportAPIService._normalize_city_name(destination)
        
        # Chercher la distance
        key1 = (origine_norm, destination_norm)
        key2 = (destination_norm, origine_norm)
        
        distance_km = distances_matrix.get(key1) or distances_matrix.get(key2)
        
        if not distance_km:
            # Distance par défaut basée sur une estimation
            distance_km = 150.0
        
        # Calculer la durée (vitesse moyenne 60 km/h)
        duration_hours = round(distance_km / 60, 2)
        
        return {
            'distance_km': distance_km,
            'duration_hours': duration_hours,
            'duration_minutes': round(duration_hours * 60),
            'duration_seconds': round(duration_hours * 3600),
            'origine_coords': None,
            'destination_coords': None,
            'success': True,
            'source': 'fallback'
        }

    @staticmethod
    def _normalize_city_name(city_name: str) -> str:
        """Normalise le nom d'une ville pour la recherche"""
        city_mapping = {
            'casa': 'casablanca',
            'rbat': 'rabat',
            'marrakech': 'marrakech',
            'marrakesh': 'marrakech',
            'fez': 'fes',
            'fès': 'fes',
            'tangier': 'tanger',
            'agadir': 'agadir',
            'meknes': 'meknes',
            'meknès': 'meknes',
            'oujda': 'oujda',
            'kenitra': 'kenitra',
            'kénitra': 'kenitra',
            'tétouan': 'tetouan',
            'tetouan': 'tetouan'
        }
        
        normalized = city_name.lower().strip()
        
        # Chercher dans le mapping
        for key, value in city_mapping.items():
            if key in normalized:
                return value
        
        # Chercher les principales villes dans le texte
        for city in ['casablanca', 'rabat', 'marrakech', 'fes', 'tanger', 'agadir', 'meknes', 'oujda']:
            if city in normalized:
                return city
        
        return normalized

    @staticmethod
    def calculate_estimated_price(distance_km: float, poids_kg: float, priorite: str = 'normale') -> Decimal:
        """Calcule un prix estimé pour le transport"""
        # Tarifs de base (en DH)
        tarif_base_km = Decimal('3.5')  # 3.5 DH par km
        tarif_poids = Decimal('0.8')    # 0.8 DH par kg
        
        # Multiplicateurs selon la priorité
        multiplicateurs = {
            'basse': Decimal('0.9'),
            'normale': Decimal('1.0'),
            'haute': Decimal('1.3'),
            'urgente': Decimal('1.6')
        }
        
        multiplicateur = multiplicateurs.get(priorite, Decimal('1.0'))
        
        # Calcul de base
        prix_distance = Decimal(str(distance_km)) * tarif_base_km
        prix_poids = Decimal(str(poids_kg)) * tarif_poids
        
        # Prix minimum
        prix_minimum = Decimal('50.0')
        
        prix_total = max(prix_minimum, (prix_distance + prix_poids) * multiplicateur)
        
        return prix_total.quantize(Decimal('0.01'))

    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """Valide des coordonnées GPS"""
        try:
            lat = float(latitude)
            lng = float(longitude)
            
            # Vérifier les limites du Maroc (approximatives)
            # Latitude: 21° à 36° N
            # Longitude: -17° à -1° W
            return (21.0 <= lat <= 36.0) and (-17.0 <= lng <= -1.0)
            
        except (ValueError, TypeError):
            return False