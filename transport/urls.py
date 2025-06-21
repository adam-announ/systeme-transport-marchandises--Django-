# transport/urls.py - Version mise à jour avec toutes les fonctionnalités
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views, transporteur_views, planificateur_views

urlpatterns = [
    # URLs publiques
    path('', views.index, name='index'),
    path('inscription/', views.inscription, name='inscription'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # URLs pour les commandes (clients)
    path('commandes/', views.liste_commandes, name='liste_commandes'),
    path('commande/creer/', views.creer_commande, name='creer_commande'),
    path('commande/<int:commande_id>/suivre/', views.suivre_commande, name='suivre_commande'),
    path('commande/<int:commande_id>/supprimer/', views.supprimer_commande, name='supprimer_commande'),
    path('rapport/', views.generer_rapport, name='generer_rapport'),
    
    # URLs pour les transporteurs
    path('transporteur/dashboard/', transporteur_views.dashboard_transporteur, name='dashboard_transporteur'),
    path('transporteur/mission/<int:mission_id>/', transporteur_views.voir_mission, name='voir_mission'),
    path('transporteur/mission/<int:mission_id>/statut/', transporteur_views.mettre_a_jour_statut, name='mettre_a_jour_statut'),
    path('transporteur/mission/<int:mission_id>/incident/', transporteur_views.notifier_incident, name='notifier_incident'),
    path('transporteur/mission/<int:mission_id>/bon-livraison/', transporteur_views.generer_bon_livraison, name='generer_bon_livraison'),
    path('transporteur/notification/<int:notification_id>/lue/', transporteur_views.marquer_notification_lue, name='marquer_notification_lue'),
    path('transporteur/disponibilite/', transporteur_views.basculer_disponibilite, name='basculer_disponibilite'),
    
    # URLs pour le planificateur
    path('planificateur/dashboard/', planificateur_views.dashboard_planificateur, name='dashboard_planificateur'),
    path('planificateur/commande/<int:commande_id>/affecter/', planificateur_views.affecter_commande, name='affecter_commande'),
    path('planificateur/optimiser/', planificateur_views.optimiser_itineraires, name='optimiser_itineraires'),
    path('planificateur/trafic/', planificateur_views.donnees_trafic, name='donnees_trafic'),
    path('planificateur/meteo/', planificateur_views.donnees_meteo, name='donnees_meteo'),
    path('planificateur/api/temps-reel/', planificateur_views.api_donnees_temps_reel, name='api_donnees_temps_reel'),
]