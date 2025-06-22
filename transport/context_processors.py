# transport/context_processors.py
from django.conf import settings

def google_maps_key(request):
    """Context processor pour rendre la clé Google Maps disponible dans tous les templates"""
    return {
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY
    }