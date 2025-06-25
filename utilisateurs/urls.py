# utilisateurs/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ==================== PAGES PUBLIQUES ====================
    path('', views.accueil, name='accueil'),
    path('services/gestion-commandes/', views.gestion_commandes, name='gestion_commandes'),
    path('services/optimisation-tournees/', views.optimisation_tournees, name='optimisation_tournees'),
    path('services/suivi-temps-reel/', views.suivi_temps_reel, name='suivi_temps_reel'),
    path('contact/', views.contact, name='contact'),
    
    # ==================== AUTHENTIFICATION ====================
    path('auth/login/', views.login_view, name='login'),
    path('auth/register/', views.register_view, name='register'),
    path('auth/logout/', views.logout_view, name='logout'),
    
    # ==================== DASHBOARD ADMIN ====================
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/create/', views.admin_create_user, name='admin_create_user'),
    path('admin/users/<int:user_id>/edit/', views.admin_edit_user, name='admin_edit_user'),
    path('admin/users/<int:user_id>/toggle/', views.admin_toggle_user, name='admin_toggle_user'),
    path('admin/commandes/', views.admin_commandes, name='admin_commandes'),
    path('admin/reports/', views.admin_reports, name='admin_reports'),
    path('admin/system-config/', views.admin_system_config, name='admin_system_config'),
    path('admin/notifications/', views.admin_notifications, name='admin_notifications'),
    
    # ==================== DASHBOARD CLIENT ====================
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),
    path('client/commandes/', views.client_commandes, name='client_commandes'),
    path('client/commandes/nouvelle/', views.client_nouvelle_commande, name='client_nouvelle_commande'),
    path('client/commandes/<int:commande_id>/', views.client_commande_detail, name='client_commande_detail'),
    path('client/commandes/<int:commande_id>/suivi/', views.client_suivi_commande, name='client_suivi_commande'),
    path('client/commandes/<int:commande_id>/annuler/', views.client_annuler_commande, name='client_annuler_commande'),
    path('client/profil/', views.client_profil, name='client_profil'),
    path('client/factures/', views.client_factures, name='client_factures'),
    
    # ==================== DASHBOARD TRANSPORTEUR ====================
    path('transporteur/dashboard/', views.transporteur_dashboard, name='transporteur_dashboard'),
    path('transporteur/commandes/', views.transporteur_commandes, name='transporteur_commandes'),
    path('transporteur/commandes/<int:commande_id>/accept/', views.transporteur_accept_commande, name='transporteur_accept_commande'),
    path('transporteur/livraisons/', views.transporteur_livraisons, name='transporteur_livraisons'),
    path('transporteur/livraisons/<int:livraison_id>/update/', views.transporteur_update_livraison, name='transporteur_update_livraison'),
    path('transporteur/vehicules/', views.transporteur_vehicules, name='transporteur_vehicules'),
    path('transporteur/vehicules/add/', views.transporteur_add_vehicule, name='transporteur_add_vehicule'),
    path('transporteur/vehicules/<int:vehicule_id>/edit/', views.transporteur_edit_vehicule, name='transporteur_edit_vehicule'),
    path('transporteur/tournees/', views.transporteur_tournees, name='transporteur_tournees'),
    path('transporteur/tournees/<int:tournee_id>/', views.transporteur_tournee_detail, name='transporteur_tournee_detail'),
    path('transporteur/itineraire/', views.transporteur_itineraire, name='transporteur_itineraire'),
    path('transporteur/profil/', views.transporteur_profil, name='transporteur_profil'),
    
    # ==================== DASHBOARD PLANIFICATEUR ====================
    path('planificateur/dashboard/', views.planificateur_dashboard, name='planificateur_dashboard'),
    path('planificateur/commandes/', views.planificateur_commandes, name='planificateur_commandes'),
    path('planificateur/tournees/', views.planificateur_tournees, name='planificateur_tournees'),
    path('planificateur/tournees/nouvelle/', views.planificateur_create_tournee, name='planificateur_create_tournee'),
    path('planificateur/tournees/<int:tournee_id>/', views.planificateur_tournee_detail, name='planificateur_tournee_detail'),
    path('planificateur/tournees/<int:tournee_id>/optimiser/', views.planificateur_optimiser_tournee, name='planificateur_optimiser_tournee'),
    path('planificateur/tournees/<int:tournee_id>/replanifier/', views.planificateur_replanifier_tournee, name='planificateur_replanifier_tournee'),
    path('planificateur/planification-auto/', views.planificateur_planification_auto, name='planificateur_planification_auto'),
    path('planificateur/suggestions/', views.planificateur_suggestions, name='planificateur_suggestions'),
    path('planificateur/analytics/', views.planificateur_analytics, name='planificateur_analytics'),
    path('planificateur/profil/', views.planificateur_profil, name='planificateur_profil'),
    
    # ==================== API AJAX ====================
    # APIs de base
    path('api/commandes/<int:commande_id>/assign/', views.assign_commande, name='assign_commande'),
    path('api/livraisons/<int:livraison_id>/status/', views.update_livraison_status, name='update_livraison_status'),
    path('api/notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    
    # APIs détaillées
    path('api/commandes/<int:commande_id>/details/', views.commande_details_api, name='commande_details_api'),
    path('api/vehicules/<int:vehicule_id>/', views.vehicule_details_api, name='vehicule_details_api'),
    path('api/vehicules/<int:vehicule_id>/update/', views.vehicule_update_api, name='vehicule_update_api'),
    path('api/vehicules/<int:vehicule_id>/toggle/', views.vehicule_toggle_api, name='vehicule_toggle_api'),
    
    # APIs de vérification temps réel
    path('api/commandes/check-new/', views.check_new_commandes, name='check_new_commandes'),
    path('api/livraisons/check-updates/', views.check_livraisons_updates, name='check_livraisons_updates'),
    path('api/notifications/count/', views.get_notifications_count, name='get_notifications_count'),
    
    # APIs Planificateur
    path('api/transporteur/<int:transporteur_id>/vehicules/', views.get_vehicules_transporteur, name='get_vehicules_transporteur'),
    path('api/calculer-distance/', views.calculer_distance_api, name='calculer_distance_api'),
    path('api/planification/auto/', views.planification_automatique_api, name='planification_automatique_api'),
    path('api/planification/capacite/', views.analyser_capacite_api, name='analyser_capacite_api'),
    path('api/tournees/<int:tournee_id>/optimiser/', views.optimiser_tournee_api, name='optimiser_tournee_api'),
    path('api/suggestions/regroupements/', views.suggestions_regroupements_api, name='suggestions_regroupements_api'),
    
    # APIs météo et transport
    path('api/weather/<str:city>/', views.weather_info_api, name='weather_info_api'),
    path('api/route/optimize/', views.optimize_route_api, name='optimize_route_api'),
    path('api/estimation/prix/', views.estimate_price_api, name='estimate_price_api'),
    
    # APIs de suivi
    path('api/livraisons/<int:livraison_id>/position/', views.update_position_livraison, name='update_position_livraison'),
    path('api/tournees/<int:tournee_id>/progress/', views.get_tournee_progress, name='get_tournee_progress'),
    
    # APIs de reporting
    path('api/reports/performance/', views.performance_report_api, name='performance_report_api'),
    path('api/reports/planification/', views.planification_report_api, name='planification_report_api'),
    path('api/analytics/transporteur/<int:transporteur_id>/', views.transporteur_analytics_api, name='transporteur_analytics_api'),
]