# transport/urls.py - URLs optimisées et organisées

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==========================================
    # AUTHENTIFICATION
    # ==========================================
    path('inscription/', views.inscription, name='inscription'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ==========================================
    # DASHBOARDS
    # ==========================================
    path('client/', views.client_dashboard, name='client_dashboard'),
    path('transporteur/', views.transporteur_dashboard, name='transporteur_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # ==========================================
    # GESTION COMMANDES (CLIENT)
    # ==========================================
    path('commande/creer/', views.creer_commande, name='creer_commande'),
    path('commande/<int:commande_id>/suivre/', views.suivre_commande, name='suivre_commande'),
    path('commandes/', views.liste_commandes, name='liste_commandes'),
    path('rapport/', views.generer_rapport, name='generer_rapport'),
    
    # ==========================================
    # GESTION MISSIONS (TRANSPORTEUR)
    # ==========================================
    path('mission/<int:mission_id>/', views.voir_mission, name='voir_mission'),
    path('mission/<int:mission_id>/statut/', views.mettre_a_jour_statut, name='mettre_a_jour_statut'),
    path('mission/<int:mission_id>/incident/', views.notifier_incident, name='notifier_incident'),
    
    # ==========================================
    # ADMINISTRATION
    # ==========================================
    path('admin/commande/<int:commande_id>/affecter/', views.affecter_commande, name='affecter_commande'),
    path('admin/utilisateurs/', views.gestion_utilisateurs, name='gestion_utilisateurs'),
    
    # ==========================================
    # API ENDPOINTS
    # ==========================================
    path('api/notifications/count/', views.api_notifications_count, name='api_notifications_count'),
    path('api/notification/<int:notification_id>/lue/', views.api_marquer_notification_lue, name='api_marquer_notification_lue'),
    
    # ==========================================
    # PAGE D'ACCUEIL
    # ==========================================
    path('', views.index, name='index'),
]

# transport_system/urls.py - URLs principales optimisées

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Application principale
    path('', include('transport.urls')),
    
    # API REST
    path('api/', include('api.urls')),
    
    # Admin Django (renommé pour éviter conflits)
    path('django-admin/', admin.site.urls),
]

# Servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)