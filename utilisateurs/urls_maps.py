# utilisateurs/urls_maps.py

from django.urls import path
from .views_maps import (
    GeocodeView,
    OptimizeRouteView,
    DistanceMatrixView,
    TravelTimeView,
    CommandesGeocodeView,
    OptimizeTourneeView,
    MapProvidersStatusView,
    SaveApiKeyView,
    bulk_optimize_commandes,
    analyze_delivery_zones
)

# URLs pour les APIs cartographiques
maps_urlpatterns = [
    # APIs de base
    path('api/maps/geocode/', GeocodeView.as_view(), name='api_geocode'),
    path('api/maps/optimize-route/', OptimizeRouteView.as_view(), name='api_optimize_route'),
    path('api/maps/distance-matrix/', DistanceMatrixView.as_view(), name='api_distance_matrix'),
    path('api/maps/travel-time/', TravelTimeView.as_view(), name='api_travel_time'),
    
    # APIs spécifiques aux commandes
    path('api/maps/commandes/geocode/', CommandesGeocodeView.as_view(), name='api_commandes_geocode'),
    path('api/maps/tournee/optimize/', OptimizeTourneeView.as_view(), name='api_tournee_optimize'),
    
    # Configuration et statut
    path('api/maps/providers/status/', MapProvidersStatusView.as_view(), name='api_maps_providers_status'),
    path('api/maps/save-api-key/', SaveApiKeyView.as_view(), name='api_save_api_key'),
    
    # APIs avancées pour planificateurs
    path('api/maps/bulk-optimize/', bulk_optimize_commandes, name='api_bulk_optimize'),
    path('api/maps/analyze-zones/', analyze_delivery_zones, name='api_analyze_zones'),
]

# À ajouter dans le fichier principal urls.py
"""
Dans utilisateurs/urls.py, ajouter :

from .urls_maps import maps_urlpatterns

urlpatterns = [
    # Vos URLs existantes...
    
] + maps_urlpatterns
"""