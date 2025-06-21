# transport/api_integrations.py
import os
import requests
import googlemaps
from datetime import datetime
import openrouteservice
from openrouteservice import convert
import json
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class APIManager:
    """Gestionnaire centralisé pour toutes les API externes"""
    
    def __init__(self):
        self.google_maps_key = os.getenv('GOOGLE_MAPS_API_KEY', '5b3ce3597851110001cf6248e5502527fc534e09872f5341eb32c63e')
        self.openweather_key = os.getenv('OPENWEATHERMAP_API_KEY', '445013d62878273453742b5ef6b260ce')
        self.ors_key = os.getenv('OPENROUTESERVICE_API_KEY', '5b3ce3597851110001cf6248e5502527fc534e09872f5341eb32c63e')
        
        # Initialiser les clients
        self.gmaps = googlemaps.Client(key=self.google_maps_key) if self.google_maps_key else None
        self.ors_client = openrouteservice.Client(key=self.ors_key) if self.ors_key else None

class GeocodeService:
    """Service de géocodage pour convertir adresses en coordonnées"""
    
    def __init__(self):
        self.api_manager = APIManager()
    
    def geocode_address(self, adresse_obj):
        """Géocoder une adresse et retourner les coordonnées"""
        cache_key = f"geocode_{adresse_obj.rue}_{adresse_obj.ville}_{adresse_obj.code_postal}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        address_string = f"{adresse_obj.rue}, {adresse_obj.code_postal} {adresse_obj.ville}, {adresse_obj.pays}"
        
        try:
            # Essayer d'abord avec Google Maps
            if self.api_manager.gmaps:
                result = self.api_manager.gmaps.geocode(address_string)
                if result:
                    location = result[0]['geometry']['location']
                    coords = {
                        'lat': location['lat'],
                        'lng': location['lng'],
                        'formatted_address': result[0]['formatted_address']
                    }
                    cache.set(cache_key, coords, 86400)  # Cache 24h
                    return coords
            
            # Fallback sur OpenRouteService
            if self.api_manager.ors_client:
                result = self.api_manager.ors_client.pelias_search(text=address_string)
                if result and result['features']:
                    coords = {
                        'lat': result['features'][0]['geometry']['coordinates'][1],
                        'lng': result['features'][0]['geometry']['coordinates'][0],
                        'formatted_address': result['features'][0]['properties']['label']
                    }
                    cache.set(cache_key, coords, 86400)
                    return coords
                    
        except Exception as e:
            logger.error(f"Erreur géocodage: {e}")
        
        # Coordonnées par défaut (Casablanca)
        return {'lat': 33.5731, 'lng': -7.5898, 'formatted_address': address_string}

class RoutingService:
    """Service de calcul d'itinéraires optimisés"""
    
    def __init__(self):
        self.api_manager = APIManager()
        self.geocode_service = GeocodeService()
    
    def calculate_route(self, origin_address, destination_address, waypoints=None, optimize=True):
        """Calculer l'itinéraire optimal entre deux adresses"""
        # Géocoder les adresses
        origin_coords = self.geocode_service.geocode_address(origin_address)
        dest_coords = self.geocode_service.geocode_address(destination_address)
        
        cache_key = f"route_{origin_coords['lat']}_{origin_coords['lng']}_{dest_coords['lat']}_{dest_coords['lng']}"
        cached_route = cache.get(cache_key)
        
        if cached_route:
            return cached_route
        
        try:
            # Utiliser OpenRouteService pour le calcul d'itinéraire
            if self.api_manager.ors_client:
                coords = [[origin_coords['lng'], origin_coords['lat']], 
                         [dest_coords['lng'], dest_coords['lat']]]
                
                # Ajouter les waypoints si fournis
                if waypoints:
                    for wp in waypoints:
                        wp_coords = self.geocode_service.geocode_address(wp)
                        coords.insert(-1, [wp_coords['lng'], wp_coords['lat']])
                
                # Calculer l'itinéraire
                route = self.api_manager.ors_client.directions(
                    coordinates=coords,
                    profile='driving-car',
                    format='geojson',
                    optimize_waypoints=optimize,
                    instructions=True,
                    language='fr'
                )
                
                if route and route['features']:
                    feature = route['features'][0]
                    properties = feature['properties']
                    
                    # Extraire les informations
                    route_data = {
                        'distance': properties['segments'][0]['distance'] / 1000,  # km
                        'duration': properties['segments'][0]['duration'] / 60,    # minutes
                        'polyline': feature['geometry'],
                        'instructions': self._parse_instructions(properties['segments'][0]['steps']),
                        'bbox': feature['bbox'],
                        'fuel_estimate': self._estimate_fuel(properties['segments'][0]['distance'] / 1000),
                        'toll_estimate': self._estimate_tolls(properties['segments'][0]['distance'] / 1000)
                    }
                    
                    cache.set(cache_key, route_data, 3600)  # Cache 1h
                    return route_data
            
            # Fallback avec Google Maps
            if self.api_manager.gmaps:
                result = self.api_manager.gmaps.directions(
                    origin=f"{origin_coords['lat']},{origin_coords['lng']}",
                    destination=f"{dest_coords['lat']},{dest_coords['lng']}",
                    waypoints=waypoints,
                    optimize_waypoints=optimize,
                    mode="driving",
                    language="fr"
                )
                
                if result:
                    leg = result[0]['legs'][0]
                    route_data = {
                        'distance': leg['distance']['value'] / 1000,
                        'duration': leg['duration']['value'] / 60,
                        'polyline': result[0]['overview_polyline']['points'],
                        'instructions': [{'text': step['html_instructions'], 
                                        'distance': step['distance']['value']} 
                                       for step in leg['steps']],
                        'fuel_estimate': self._estimate_fuel(leg['distance']['value'] / 1000),
                        'toll_estimate': self._estimate_tolls(leg['distance']['value'] / 1000)
                    }
                    cache.set(cache_key, route_data, 3600)
                    return route_data
                    
        except Exception as e:
            logger.error(f"Erreur calcul itinéraire: {e}")
        
        # Valeurs par défaut
        return {
            'distance': 50,
            'duration': 60,
            'polyline': None,
            'instructions': [],
            'fuel_estimate': 5,
            'toll_estimate': 10
        }
    
    def _parse_instructions(self, steps):
        """Parser les instructions de navigation"""
        instructions = []
        for step in steps:
            instructions.append({
                'text': step.get('instruction', ''),
                'distance': step.get('distance', 0),
                'duration': step.get('duration', 0),
                'type': step.get('type', ''),
                'name': step.get('name', '')
            })
        return instructions
    
    def _estimate_fuel(self, distance_km):
        """Estimer la consommation de carburant"""
        # Consommation moyenne: 8L/100km pour un camion
        consumption_rate = 8
        fuel_liters = (distance_km * consumption_rate) / 100
        fuel_price_per_liter = 12  # MAD
        return round(fuel_liters * fuel_price_per_liter, 2)
    
    def _estimate_tolls(self, distance_km):
        """Estimer les frais de péage"""
        # Estimation simplifiée: 0.30 MAD/km sur autoroute
        if distance_km > 50:  # Probablement autoroute
            return round(distance_km * 0.30, 2)
        return 0

class WeatherService:
    """Service météo pour obtenir les conditions actuelles et prévisions"""
    
    def __init__(self):
        self.api_manager = APIManager()
        self.geocode_service = GeocodeService()
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    def get_current_weather(self, address):
        """Obtenir la météo actuelle pour une adresse"""
        coords = self.geocode_service.geocode_address(address)
        
        cache_key = f"weather_{coords['lat']}_{coords['lng']}"
        cached_weather = cache.get(cache_key)
        
        if cached_weather:
            return cached_weather
        
        try:
            url = f"{self.base_url}/weather"
            params = {
                'lat': coords['lat'],
                'lon': coords['lng'],
                'appid': self.api_manager.openweather_key,
                'units': 'metric',
                'lang': 'fr'
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                
                weather_data = {
                    'temperature': data['main']['temp'],
                    'feels_like': data['main']['feels_like'],
                    'description': data['weather'][0]['description'],
                    'icon': data['weather'][0]['icon'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind']['speed'],
                    'wind_direction': data['wind'].get('deg', 0),
                    'visibility': data.get('visibility', 10000),
                    'clouds': data['clouds']['all'],
                    'conditions': self._categorize_conditions(data['weather'][0]['id']),
                    'alerts': self._check_weather_alerts(data)
                }
                
                cache.set(cache_key, weather_data, 1800)  # Cache 30 min
                return weather_data
                
        except Exception as e:
            logger.error(f"Erreur météo: {e}")
        
        return {
            'temperature': 20,
            'description': 'Données non disponibles',
            'conditions': 'normal',
            'alerts': []
        }
    
    def get_route_weather_forecast(self, origin_address, destination_address, departure_time=None):
        """Obtenir les prévisions météo le long d'un itinéraire"""
        if not departure_time:
            departure_time = datetime.now()
        
        # Obtenir la météo aux deux extrémités
        origin_weather = self.get_current_weather(origin_address)
        dest_weather = self.get_current_weather(destination_address)
        
        # Analyser les conditions
        worst_conditions = self._get_worst_conditions([origin_weather, dest_weather])
        
        return {
            'origin': origin_weather,
            'destination': dest_weather,
            'worst_conditions': worst_conditions,
            'recommendations': self._get_weather_recommendations(worst_conditions)
        }
    
    def _categorize_conditions(self, weather_id):
        """Catégoriser les conditions météo"""
        if weather_id < 300:  # Orage
            return 'danger'
        elif weather_id < 600:  # Pluie
            return 'mauvais'
        elif weather_id < 700:  # Neige
            return 'danger'
        elif weather_id < 800:  # Brouillard
            return 'attention'
        elif weather_id == 800:  # Clair
            return 'excellent'
        else:  # Nuageux
            return 'normal'
    
    def _check_weather_alerts(self, data):
        """Vérifier les alertes météo"""
        alerts = []
        
        # Vent fort
        if data['wind']['speed'] > 50:
            alerts.append({
                'type': 'vent',
                'level': 'danger',
                'message': 'Vents violents - Circulation déconseillée'
            })
        elif data['wind']['speed'] > 30:
            alerts.append({
                'type': 'vent',
                'level': 'attention',
                'message': 'Vents forts - Prudence recommandée'
            })
        
        # Visibilité
        if data.get('visibility', 10000) < 1000:
            alerts.append({
                'type': 'visibilite',
                'level': 'danger',
                'message': 'Visibilité réduite - Danger'
            })
        
        return alerts
    
    def _get_worst_conditions(self, weather_list):
        """Déterminer les pires conditions sur un trajet"""
        conditions_priority = {'danger': 4, 'mauvais': 3, 'attention': 2, 'normal': 1, 'excellent': 0}
        worst = 'excellent'
        
        for weather in weather_list:
            if conditions_priority.get(weather['conditions'], 0) > conditions_priority[worst]:
                worst = weather['conditions']
        
        return worst
    
    def _get_weather_recommendations(self, conditions):
        """Obtenir des recommandations selon les conditions"""
        recommendations = {
            'danger': {
                'delay_recommended': True,
                'message': 'Report du transport fortement recommandé',
                'speed_reduction': 50,
                'extra_time': 100
            },
            'mauvais': {
                'delay_recommended': False,
                'message': 'Prudence extrême requise',
                'speed_reduction': 30,
                'extra_time': 50
            },
            'attention': {
                'delay_recommended': False,
                'message': 'Vigilance accrue nécessaire',
                'speed_reduction': 20,
                'extra_time': 30
            },
            'normal': {
                'delay_recommended': False,
                'message': 'Conditions acceptables',
                'speed_reduction': 0,
                'extra_time': 0
            },
            'excellent': {
                'delay_recommended': False,
                'message': 'Conditions idéales',
                'speed_reduction': 0,
                'extra_time': 0
            }
        }
        
        return recommendations.get(conditions, recommendations['normal'])

class TrafficService:
    """Service pour obtenir les informations de trafic en temps réel"""
    
    def __init__(self):
        self.api_manager = APIManager()
    
    def get_traffic_info(self, origin_coords, dest_coords):
        """Obtenir les informations de trafic"""
        try:
            if self.api_manager.gmaps:
                # Utiliser l'API Distance Matrix avec departure_time pour avoir le trafic
                result = self.api_manager.gmaps.distance_matrix(
                    origins=[f"{origin_coords['lat']},{origin_coords['lng']}"],
                    destinations=[f"{dest_coords['lat']},{dest_coords['lng']}"],
                    mode="driving",
                    departure_time=datetime.now(),
                    traffic_model="best_guess"
                )
                
                if result['rows'][0]['elements'][0]['status'] == 'OK':
                    element = result['rows'][0]['elements'][0]
                    
                    # Calculer le niveau de trafic
                    duration_normal = element['duration']['value']
                    duration_traffic = element.get('duration_in_traffic', {}).get('value', duration_normal)
                    
                    traffic_ratio = duration_traffic / duration_normal if duration_normal > 0 else 1
                    
                    if traffic_ratio < 1.1:
                        traffic_level = 'fluide'
                    elif traffic_ratio < 1.3:
                        traffic_level = 'normal'
                    elif traffic_ratio < 1.5:
                        traffic_level = 'dense'
                    else:
                        traffic_level = 'bloque'
                    
                    return {
                        'level': traffic_level,
                        'duration_normal': duration_normal / 60,
                        'duration_traffic': duration_traffic / 60,
                        'delay': (duration_traffic - duration_normal) / 60,
                        'speed_average': self._calculate_average_speed(traffic_level)
                    }
                    
        except Exception as e:
            logger.error(f"Erreur trafic: {e}")
        
        # Valeurs par défaut
        return {
            'level': 'normal',
            'duration_normal': 60,
            'duration_traffic': 60,
            'delay': 0,
            'speed_average': 60
        }
    
    def _calculate_average_speed(self, traffic_level):
        """Calculer la vitesse moyenne selon le niveau de trafic"""
        speeds = {
            'fluide': 80,
            'normal': 60,
            'dense': 40,
            'bloque': 20
        }
        return speeds.get(traffic_level, 60)

class NotificationService:
    """Service pour envoyer des notifications (SMS, Email, Push)"""
    
    def __init__(self):
        # Configuration des services de notification
        self.email_configured = hasattr(settings, 'EMAIL_HOST')
        self.sms_configured = False  # À implémenter avec un service SMS
        self.push_configured = False  # À implémenter avec Firebase
    
    def send_notification(self, user, message, type='email', priority='normal'):
        """Envoyer une notification à un utilisateur"""
        success = False
        
        try:
            if type == 'email' and self.email_configured:
                success = self._send_email(user, message)
            elif type == 'sms' and self.sms_configured:
                success = self._send_sms(user, message)
            elif type == 'push' and self.push_configured:
                success = self._send_push(user, message, priority)
            
            # Enregistrer dans la base
            from .models import Notification
            Notification.objects.create(
                destinataire=user,
                type='SYSTEME',
                titre=message.get('subject', 'Notification'),
                message=message.get('body', ''),
                priorite=priority.upper()
            )
            
        except Exception as e:
            logger.error(f"Erreur notification: {e}")
        
        return success
    
    def _send_email(self, user, message):
        """Envoyer un email"""
        from django.core.mail import send_mail
        
        try:
            send_mail(
                subject=message.get('subject', 'Notification Transport'),
                message=message.get('body', ''),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=message.get('html_body', None)
            )
            return True
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False
    
    def _send_sms(self, user, message):
        """Envoyer un SMS (à implémenter avec Twilio, Nexmo, etc.)"""
        # Placeholder pour l'implémentation SMS
        return False
    
    def _send_push(self, user, message, priority):
        """Envoyer une notification push (à implémenter avec Firebase)"""
        # Placeholder pour l'implémentation push
        return False

# Instance globale des services
geocode_service = GeocodeService()
routing_service = RoutingService()
weather_service = WeatherService()
traffic_service = TrafficService()
notification_service = NotificationService()