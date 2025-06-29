# utilisateurs/services/maps_service.py

import requests
import json
import logging
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from decimal import Decimal
import time

logger = logging.getLogger(__name__)

class MapsService:
    """Service unifié pour gérer différentes APIs cartographiques"""
    
    def __init__(self):
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        self.openroute_api_key = getattr(settings, 'OPENROUTE_API_KEY', '')
        self.geoapify_api_key = getattr(settings, 'GEOAPIFY_API_KEY', '')
        self.mapbox_token = getattr(settings, 'MAPBOX_ACCESS_TOKEN', '')
        
        # Importer le service Google Maps
        from .google_maps_service import GoogleMapsService
        self.google_service = GoogleMapsService() if self.google_api_key else None
        
        # Configuration des providers disponibles
        self.providers = {
            'google': self._google_available(),
            'openroute': self._openroute_available(),
            'geoapify': self._geoapify_available(),
            'mapbox': self._mapbox_available()
        }
        
        # Provider par défaut
        self.default_provider = self._get_best_provider()
    
    def _google_available(self) -> bool:
        """Vérifier si Google Maps est disponible"""
        return bool(self.google_api_key and self.google_api_key != 'YOUR_GOOGLE_MAPS_API_KEY')
    
    def _openroute_available(self) -> bool:
        """Vérifier si OpenRoute Service est disponible"""
        return bool(self.openroute_api_key)
    
    def _mapbox_available(self) -> bool:
        """Vérifier si Mapbox est disponible"""
        return bool(self.mapbox_token)
    
    def _geoapify_available(self) -> bool:
        """Vérifier si Geoapify est disponible"""
        return bool(self.geoapify_api_key)
    
    def _get_best_provider(self) -> str:
        """Retourner le meilleur provider disponible"""
        if self.providers.get('geoapify'):
            return 'geoapify'
        elif self.providers.get('openroute'):
            return 'openroute'
        elif self.providers.get('google'):
            return 'google'
        elif self.providers.get('mapbox'):
            return 'mapbox'
        else:
            return 'fallback'
    
    def geocode_address(self, address: str, provider: str = None) -> Optional[Dict]:
        """
        Géocoder une adresse avec le provider spécifié
        
        Args:
            address: Adresse à géocoder
            provider: Provider à utiliser ('google', 'openroute', 'mapbox')
            
        Returns:
            Dict avec lat, lng et métadonnées ou None
        """
        provider = provider or self.default_provider
        
        # Vérifier le cache
        cache_key = f"geocode_{provider}_{hash(address)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            if provider == 'google' and self.providers['google']:
                result = self._geocode_google(address)
            elif provider == 'openroute' and self.providers['openroute']:
                result = self._geocode_openroute(address)
            elif provider == 'mapbox' and self.providers['mapbox']:
                result = self._geocode_mapbox(address)
            else:
                result = self._geocode_fallback(address)