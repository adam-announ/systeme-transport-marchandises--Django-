# URLs spécialisées pour les API du planificateur
from django.urls import path
from . import api_planificateur

urlpatterns = [
    # API Planification automatique
    path('api/planification/automatique/', api_planificateur.planification_automatique_api, name='planification_automatique_api'),
    path('api/planification/rapide/', api_planificateur.planification_rapide_api, name='planification_rapide_api'),
    path('api/planification/urgence/<int:commande_id>/', api_planificateur.planification_urgence_api, name='planification_urgence_api'),
    
    # API Regroupements et suggestions
    path('api/regroupements/suggestions/', api_planificateur.suggestions_regroupements_api, name='suggestions_regroupements_api'),
    path('api/regroupements/appliquer/', api_planificateur.appliquer_regroupement_api, name='appliquer_regroupement_api'),
    
    # API Optimisation
    path('api/tournees/<int:tournee_id>/optimiser/', api_planificateur.optimiser_tournee_existante_api, name='optimiser_tournee_api'),
    
    # API Données
    path('api/stats/planification/', api_planificateur.stats_planification_api, name='stats_planification_api'),
    path('api/transporteurs/disponibles/', api_planificateur.transporteurs_disponibles_api, name='transporteurs_disponibles_api'),
    path('api/transporteur/<int:transporteur_id>/vehicules/', api_planificateur.vehicules_transporteur_api, name='vehicules_transporteur_api'),
]