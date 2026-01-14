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
    path('mission/<uuid:mission_id>/statut/', views.mettre_a_jour_statut, name='mettre_a_jour_statut'),
    path('mission/<uuid:mission_id>/incident/', views.signaler_incident, name='signaler_incident'),
    path('vehicules/', views.mes_vehicules, name='mes_vehicules'),
    path('vehicules/ajouter/', views.ajouter_vehicule, name='ajouter_vehicule'),
    path('vehicules/<uuid:vehicule_id>/modifier/', views.modifier_vehicule, name='modifier_vehicule'),
    path('vehicules/<uuid:vehicule_id>/supprimer/', views.supprimer_vehicule, name='supprimer_vehicule'),
    
    # API
    path('api/missions/', views.api_mes_missions, name='api_mes_missions'),
    path('api/position/', views.api_mettre_a_jour_position, name='api_mettre_a_jour_position'),
    path('api/livraison/', views.api_confirmer_livraison, name='api_confirmer_livraison'),
    path('api/vehicules/', views.api_vehicules, name='api_vehicules'),
    path('api/vehicules/creer/', views.api_creer_vehicule, name='api_creer_vehicule'),
    path('api/vehicules/<uuid:vehicule_id>/', views.api_modifier_vehicule, name='api_modifier_vehicule'),
    path('api/vehicules/<uuid:vehicule_id>/supprimer/', views.api_supprimer_vehicule, name='api_supprimer_vehicule'),
    path('api/statut/', views.api_statut, name='api_statut'),
    path('api/incident/', views.api_incident, name='api_incident'),
]