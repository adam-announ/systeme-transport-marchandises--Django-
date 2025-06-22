# transport/urls.py - Version simple qui FONCTIONNE

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views, transporteur_views, planificateur_views, admin_views

urlpatterns = [
    # ==========================================
    # AUTHENTIFICATION
    # ==========================================
    path('inscription/', views.inscription, name='inscription'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ==========================================
    # ADMIN CUSTOM (préfixe admin/ maintenant sécurisé)
    # ==========================================
    path('admin/dashboard/', admin_views.dashboard_admin, name='admin_dashboard'),
    path('admin/utilisateurs/', admin_views.gestion_utilisateurs, name='gestion_utilisateurs'),
    path('admin/creer-compte/', admin_views.creer_compte, name='creer_compte'),
    path('admin/roles/', admin_views.gestion_roles, name='gestion_roles'),
    path('admin/journal/', admin_views.journal_activite, name='journal_activite'),
    path('admin/parametres/', admin_views.parametres_systeme, name='parametres_systeme'),
    path('admin/notifications/', admin_views.envoyer_notification_globale, name='envoyer_notification_globale'),
    path('admin/support/', admin_views.support_clients, name='support_clients'),
    path('admin/support/<int:user_id>/', admin_views.support_conversation, name='support_conversation'),
    path('admin/statistiques/', admin_views.statistiques_avancees, name='statistiques_avancees'),
    
    # ==========================================
    # PLANIFICATEUR
    # ==========================================
    path('planificateur/', planificateur_views.dashboard_planificateur, name='dashboard_planificateur'),
    path('planificateur/commande/<int:commande_id>/affecter/', planificateur_views.affecter_commande, name='affecter_commande'),
    path('planificateur/optimiser/', planificateur_views.optimiser_itineraires, name='optimiser_itineraires'),
    path('planificateur/trafic/', planificateur_views.donnees_trafic, name='donnees_trafic'),
    path('planificateur/meteo/', planificateur_views.donnees_meteo, name='donnees_meteo'),
    path('planificateur/api/temps-reel/', planificateur_views.api_donnees_temps_reel, name='api_donnees_temps_reel'),
    
    # ==========================================
    # TRANSPORTEUR
    # ==========================================
    path('transporteur/', transporteur_views.dashboard_transporteur, name='dashboard_transporteur'),
    path('transporteur/mission/<int:mission_id>/', transporteur_views.voir_mission, name='voir_mission'),
    path('transporteur/mission/<int:mission_id>/statut/', transporteur_views.mettre_a_jour_statut, name='mettre_a_jour_statut'),
    path('transporteur/mission/<int:mission_id>/incident/', transporteur_views.notifier_incident, name='notifier_incident'),
    path('transporteur/mission/<int:mission_id>/bon-livraison/', transporteur_views.generer_bon_livraison, name='generer_bon_livraison'),
    path('transporteur/notification/<int:notification_id>/lue/', transporteur_views.marquer_notification_lue, name='marquer_notification_lue'),
    path('transporteur/disponibilite/', transporteur_views.basculer_disponibilite, name='basculer_disponibilite'),
    
    # ==========================================
    # CLIENT
    # ==========================================
    path('client/', views.client_dashboard, name='client_dashboard'),
    path('commande/creer/', views.creer_commande, name='creer_commande'),
    path('commande/<int:commande_id>/suivre/', views.suivre_commande, name='suivre_commande'),
    path('commande/<int:commande_id>/supprimer/', views.supprimer_commande, name='supprimer_commande'),
    path('commandes/', views.liste_commandes, name='liste_commandes'),
    path('rapport/', views.generer_rapport, name='generer_rapport'),
    path('support/', views.messagerie_support, name='messagerie_support'),
    
    # ==========================================
    # API
    # ==========================================
    path('api/notifications/count/', views.api_notifications_count, name='api_notifications_count'),
    path('api/notification/<int:notification_id>/lue/', views.api_marquer_notification_lue, name='api_marquer_notification_lue'),
    
    # ==========================================
    # PAGES PUBLIQUES
    # ==========================================
    path('home/', views.home_modern, name='home_modern'),
    
    # ==========================================
    # PAGE D'ACCUEIL (toujours en dernier)
    # ==========================================
    path('', views.index, name='index'),
]