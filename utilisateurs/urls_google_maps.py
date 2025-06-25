# utilisateurs/urls_google_maps.py

from django.urls import path
from . import views_google_maps

app_name = 'google_maps'

urlpatterns = [
    path('', views_google_maps.google_maps_view, name='map'),
    path('leaflet/', views_google_maps.leaflet_maps_view, name='leaflet_map'),
    path('api/optimize-route/', views_google_maps.optimize_route_api, name='optimize_route'),
    path('api/geocode/', views_google_maps.geocode_api, name='geocode'),
]