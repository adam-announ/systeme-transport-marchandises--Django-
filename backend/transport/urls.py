# backend/transport/urls.py - Version corrigée
from django.urls import path
from . import views

app_name = 'transport'

urlpatterns = [
    # Pages principales
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboards
    path('client/', views.client_dashboard, name='client_dashboard'),
    path('transporteur/', views.transporteur_dashboard, name='transporteur_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('planificateur/', views.planificateur_dashboard, name='planificateur_dashboard'),
    
    # Gestion des commandes
    path('commande/creer/', views.creer_commande, name='creer_commande'),
    path('commande/suivre/<uuid:commande_id>/', views.suivre_commande, name='suivre_commande'),
    path('commandes/gerer/', views.gerer_commandes, name='gerer_commandes'),
    
    # API endpoints - Gestion des commandes
    path('api/assigner-transporteur/', views.assigner_transporteur, name='assigner_transporteur'),
    path('api/mettre-a-jour-statut/', views.mettre_a_jour_statut, name='mettre_a_jour_statut'),
    path('api/calculer-itineraire/', views.calculer_itineraire, name='calculer_itineraire'),
    
    # API endpoints - Planification
    path('api/optimiser-itineraires/', views.optimiser_itineraires, name='optimiser_itineraires'),
    path('api/assignation-automatique/', views.assignation_automatique, name='assignation_automatique'),
    path('api/planifier-livraisons/', views.planifier_livraisons, name='planifier_livraisons'),
    
    # API endpoints - Transporteurs
    path('api/toggle-disponibilite/', views.toggle_disponibilite_transporteur, name='toggle_disponibilite'),
    path('api/report-incident/', views.signaler_incident, name='signaler_incident'),
    path('api/check-new-missions/', views.verifier_nouvelles_missions, name='verifier_nouvelles_missions'),
    
    # Autres pages
    path('notifications/', views.notifications, name='notifications'),
    path('journal/', views.journal_activite, name='journal_activite'),
]