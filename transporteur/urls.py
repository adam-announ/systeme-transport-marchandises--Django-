"""
URLs pour l'interface transporteur
"""

from django.urls import path
from . import views

app_name = 'transporteur'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('missions/', views.mes_missions, name='mes_missions'),
    path('mission/<uuid:mission_id>/', views.mission_detail, name='mission_detail'),
    path('itineraire/<uuid:mission_id>/', views.itineraire_mission, name='itineraire_mission'),
    path('statut/<uuid:mission_id>/', views.mettre_a_jour_statut, name='mettre_a_jour_statut'),
    path('incident/<uuid:mission_id>/', views.signaler_incident, name='signaler_incident'),
    path('vehicules/', views.mes_vehicules, name='mes_vehicules'),
    path('vehicules/ajouter/', views.ajouter_vehicule, name='ajouter_vehicule'),
    
    # API
    path('api/missions/', views.api_mes_missions, name='api_mes_missions'),
    path('api/position/', views.api_mettre_a_jour_position, name='api_mettre_a_jour_position'),
    path('api/livraison/', views.api_confirmer_livraison, name='api_confirmer_livraison'),
    path('api/vehicules/', views.api_vehicules, name='api_vehicules'),
    path('api/statut/', views.api_statut, name='api_statut'),
    path('api/incident/', views.api_incident, name='api_incident'),
]