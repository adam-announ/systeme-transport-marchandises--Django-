"""
Configuration des APIs externes pour le système de transport
"""

import os
from decouple import config

# Configuration Google Maps API
GOOGLE_MAPS_CONFIG = {
    'API_KEY': config('GOOGLE_MAPS_API_KEY', default=''),
    'LIBRARIES': ['geometry', 'places', 'directions'],
    'REGION': 'MA',  # Maroc
    'LANGUAGE': 'fr',
    'DEFAULT_CENTER': {
        'lat': 33.5731,
        'lng': -7.5898  # Casablanca
    },
    'DEFAULT_ZOOM': 11,
    'ENDPOINTS': {
        'DIRECTIONS': 'https://maps.googleapis.com/maps/api/directions/json',
        'GEOCODING': 'https://maps.googleapis.com/maps/api/geocode/json',
        'PLACES': 'https://maps.googleapis.com/maps/api/place/nearbysearch/json',
        'DISTANCE_MATRIX': 'https://maps.googleapis.com/maps/api/distancematrix/json'
    }
}

# Configuration OpenWeather API
OPENWEATHER_CONFIG = {
    'API_KEY': config('OPENWEATHER_API_KEY', default=''),
    'BASE_URL': 'https://api.openweathermap.org/data/2.5',
    'ENDPOINTS': {
        'CURRENT': '/weather',
        'FORECAST': '/forecast',
        'ONECALL': '/onecall'
    },
    'UNITS': 'metric',
    'LANGUAGE': 'fr'
}

# Configuration OpenRoute Service
OPENROUTE_CONFIG = {
    'API_KEY': config('OPENROUTE_API_KEY', default=''),
    'BASE_URL': 'https://api.openrouteservice.org',
    'ENDPOINTS': {
        'DIRECTIONS': '/v2/directions/driving-car',
        'OPTIMIZATION': '/optimization',
        'GEOCODING': '/geocode/search'
    },
    'PROFILE': 'driving-car'
}

# Configuration Mapbox (alternative)
MAPBOX_CONFIG = {
    'ACCESS_TOKEN': config('MAPBOX_ACCESS_TOKEN', default=''),
    'BASE_URL': 'https://api.mapbox.com',
    'ENDPOINTS': {
        'DIRECTIONS': '/directions/v5/mapbox/driving',
        'OPTIMIZATION': '/optimized-trips/v1/mapbox/driving',
        'GEOCODING': '/geocoding/v5/mapbox.places'
    }
}

# Coordonnées des principales villes du Maroc
MOROCCO_CITIES = {
    'casablanca': {'lat': 33.5731, 'lng': -7.5898, 'name': 'Casablanca'},
    'rabat': {'lat': 34.0209, 'lng': -6.8416, 'name': 'Rabat'},
    'marrakech': {'lat': 31.6295, 'lng': -7.9811, 'name': 'Marrakech'},
    'fes': {'lat': 34.0331, 'lng': -5.0003, 'name': 'Fès'},
    'tanger': {'lat': 35.7595, 'lng': -5.8340, 'name': 'Tanger'},
    'agadir': {'lat': 30.4278, 'lng': -9.5981, 'name': 'Agadir'},
    'meknes': {'lat': 33.8935, 'lng': -5.5473, 'name': 'Meknès'},
    'oujda': {'lat': 34.6814, 'lng': -1.9086, 'name': 'Oujda'},
    'kenitra': {'lat': 34.2610, 'lng': -6.5802, 'name': 'Kénitra'},
    'tetouan': {'lat': 35.5889, 'lng': -5.3626, 'name': 'Tétouan'},
    'safi': {'lat': 32.2994, 'lng': -9.2372, 'name': 'Safi'},
    'mohammedia': {'lat': 33.6864, 'lng': -7.3822, 'name': 'Mohammedia'},
    'el_jadida': {'lat': 33.2316, 'lng': -8.5007, 'name': 'El Jadida'},
    'nador': {'lat': 35.1740, 'lng': -2.9287, 'name': 'Nador'}
}

# Configuration des limites d'utilisation des APIs
API_LIMITS = {
    'google_maps': {
        'requests_per_day': 25000,
        'requests_per_minute': 50,
        'cost_per_request': 0.005  # USD
    },
    'openweather': {
        'requests_per_day': 1000,
        'requests_per_minute': 60,
        'cost_per_request': 0.0  # Gratuit jusqu'à 1000/jour
    },
    'openroute': {
        'requests_per_day': 2000,
        'requests_per_minute': 40,
        'cost_per_request': 0.0  # Gratuit jusqu'à 2000/jour
    }
}

# Priorité des fournisseurs (en cas de fallback)
PROVIDER_PRIORITY = {
    'directions': ['google_maps', 'openroute', 'mapbox'],
    'geocoding': ['google_maps', 'openroute', 'mapbox'],
    'weather': ['openweather'],
    'optimization': ['google_maps', 'openroute', 'mapbox']
}

# Configuration du cache
CACHE_CONFIG = {
    'ENABLE': True,
    'TTL': {
        'directions': 3600,  # 1 heure
        'geocoding': 86400,  # 24 heures
        'weather': 1800,     # 30 minutes
        'optimization': 1800  # 30 minutes
    }
}

# Configuration des alertes
ALERTS_CONFIG = {
    'WEATHER_ALERTS': True,
    'TRAFFIC_ALERTS': True,
    'DELAY_THRESHOLD': 30,  # minutes
    'DISTANCE_THRESHOLD': 5,  # km de déviation
}

def get_api_key(provider):
    """Récupère la clé API pour un fournisseur donné"""
    keys = {
        'google_maps': GOOGLE_MAPS_CONFIG['API_KEY'],
        'openweather': OPENWEATHER_CONFIG['API_KEY'],
        'openroute': OPENROUTE_CONFIG['API_KEY'],
        'mapbox': MAPBOX_CONFIG['ACCESS_TOKEN']
    }
    return keys.get(provider, '')

def is_api_available(provider):
    """Vérifie si une API est disponible (clé configurée)"""
    return bool(get_api_key(provider))

def get_available_providers(service_type):
    """Retourne les fournisseurs disponibles pour un type de service"""
    providers = PROVIDER_PRIORITY.get(service_type, [])
    return [p for p in providers if is_api_available(p)]

def get_city_coordinates(city_name):
    """Récupère les coordonnées d'une ville marocaine"""
    city_key = city_name.lower().replace(' ', '_')
    return MOROCCO_CITIES.get(city_key, None)

def estimate_api_cost(provider, requests_count):
    """Estime le coût d'utilisation d'une API"""
    if provider in API_LIMITS:
        cost_per_request = API_LIMITS[provider].get('cost_per_request', 0)
        return requests_count * cost_per_request
    return 0

# Instructions pour obtenir les clés API
API_SETUP_INSTRUCTIONS = {
    'google_maps': {
        'url': 'https://console.cloud.google.com/',
        'steps': [
            '1. Créer un projet Google Cloud',
            '2. Activer les APIs: Maps JavaScript, Directions, Geocoding',
            '3. Créer une clé API',
            '4. Configurer les restrictions (domaines, IPs)',
            '5. Ajouter la clé dans le fichier .env'
        ],
        'apis_required': [
            'Maps JavaScript API',
            'Directions API',
            'Geocoding API',
            'Distance Matrix API'
        ]
    },
    'openweather': {
        'url': 'https://openweathermap.org/api',
        'steps': [
            '1. S\'inscrire sur OpenWeatherMap',
            '2. Confirmer l\'email',
            '3. Récupérer la clé API gratuite',
            '4. Ajouter la clé dans le fichier .env'
        ],
        'free_tier': '1000 appels/jour gratuits'
    },
    'openroute': {
        'url': 'https://openrouteservice.org/',
        'steps': [
            '1. S\'inscrire sur OpenRoute Service',
            '2. Confirmer l\'email',
            '3. Récupérer la clé API gratuite',
            '4. Ajouter la clé dans le fichier .env'
        ],
        'free_tier': '2000 appels/jour gratuits'
    }
}

def print_setup_instructions():
    """Affiche les instructions de configuration des APIs"""
    print("🔧 CONFIGURATION DES APIS EXTERNES")
    print("=" * 50)
    
    for provider, info in API_SETUP_INSTRUCTIONS.items():
        print(f"\n📍 {provider.upper()}")
        print(f"URL: {info['url']}")
        
        if 'free_tier' in info:
            print(f"Gratuit: {info['free_tier']}")
        
        print("Étapes:")
        for step in info['steps']:
            print(f"  {step}")
        
        if 'apis_required' in info:
            print("APIs requises:")
            for api in info['apis_required']:
                print(f"  - {api}")

if __name__ == '__main__':
    print_setup_instructions()