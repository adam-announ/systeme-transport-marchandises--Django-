"""
URLs pour l'interface planificateur
"""

from django.urls import path
from . import views

app_name = 'planificateur'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('commandes/', views.gestion_commandes, name='gestion_commandes'),
    path('optimiser/<uuid:commande_id>/', views.optimiser_itineraire, name='optimiser_itineraire'),
    path('affecter/<uuid:commande_id>/', views.affecter_transporteur, name='affecter_transporteur'),
    
    # API
    path('api/optimiser/', views.api_optimiser_itineraire, name='api_optimiser_itineraire'),
    path('api/transporteurs/', views.api_transporteurs_disponibles, name='api_transporteurs_disponibles'),
]