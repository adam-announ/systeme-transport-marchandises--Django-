from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# URLs principales du projet
urlpatterns = [
    # Interface d'administration Django
    path('admin/', admin.site.urls),
    
    # API REST
    path('api/', include('transport.api_urls')),
    
    # Documentation API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Interface traditionnelle Django (optionnel)
    path('', include('transport.urls')),
]

# Servir les fichiers média et statiques en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar en développement
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# URLs pour l'application transport
# transport/urls.py
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
    
    # Autres pages
    path('notifications/', views.notifications, name='notifications'),
    path('journal/', views.journal_activite, name='journal_activite'),
]

# URLs API REST
# transport/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import views_api

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'commandes', views_api.CommandeViewSet, basename='commande')
router.register(r'transporteurs', views_api.TransporteurViewSet, basename='transporteur')
router.register(r'clients', views_api.ClientViewSet, basename='client')
router.register(r'incidents', views_api.IncidentViewSet, basename='incident')
router.register(r'notifications', views_api.NotificationViewSet, basename='notification')
router.register(r'journal', views_api.JournalViewSet, basename='journal')

urlpatterns = [
    # Authentification
    path('auth/login/', views_api.LoginView.as_view(), name='api_login'),
    path('auth/logout/', views_api.LogoutView.as_view(), name='api_logout'),
    path('auth/register/', views_api.RegisterView.as_view(), name='api_register'),
    path('auth/user/', views_api.CurrentUserView.as_view(), name='current_user'),
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    path('auth/refresh/', views_api.RefreshTokenView.as_view(), name='refresh_token'),
    
    # Endpoints du router
    path('', include(router.urls)),
    
    # Endpoints personnalisés
    path('dashboard/', views_api.dashboard_data, name='dashboard_data'),
    path('dashboard/client/', views_api.ClientDashboardView.as_view(), name='client_dashboard_api'),
    path('dashboard/transporteur/', views_api.TransporteurDashboardView.as_view(), name='transporteur_dashboard_api'),
    path('dashboard/admin/', views_api.AdminDashboardView.as_view(), name='admin_dashboard_api'),
    path('dashboard/planificateur/', views_api.PlanificateurDashboardView.as_view(), name='planificateur_dashboard_api'),
    
    # Gestion des commandes
    path('commandes/<uuid:pk>/assigner-transporteur/', views_api.AssignTransporteurView.as_view(), name='assign_transporteur'),
    path('commandes/<uuid:pk>/changer-statut/', views_api.ChangeStatusView.as_view(), name='change_status'),
    path('commandes/<uuid:pk>/tracking/', views_api.TrackingListView.as_view(), name='commande_tracking'),
    path('commandes/<uuid:pk>/bon-livraison/', views_api.BonLivraisonView.as_view(), name='bon_livraison'),
    
    # Gestion des transporteurs
    path('transporteurs/<int:pk>/toggle-disponibilite/', views_api.ToggleDisponibiliteView.as_view(), name='toggle_disponibilite'),
    path('transporteurs/<int:pk>/position/', views_api.UpdatePositionView.as_view(), name='update_position'),
    path('transporteurs/disponibles/', views_api.TransporteursDisponiblesView.as_view(), name='transporteurs_disponibles'),
    
    # Planification et optimisation
    path('assignation-automatique/', views_api.assignation_automatique, name='assignation_automatique'),
    path('optimiser-itineraires/', views_api.OptimiserItinerairesView.as_view(), name='optimiser_itineraires'),
    path('calculer-itineraire/', views_api.calculer_itineraire_api, name='calculer_itineraire'),
    
    # Géolocalisation et cartes
    path('geocoding/', views_api.GeocodingView.as_view(), name='geocoding'),
    path('reverse-geocoding/', views_api.ReverseGeocodingView.as_view(), name='reverse_geocoding'),
    path('traffic-info/', views_api.TrafficInfoView.as_view(), name='traffic_info'),
    path('weather-info/', views_api.WeatherInfoView.as_view(), name='weather_info'),
    
    # Rapports et exports
    path('export/commandes/', views_api.ExportCommandesView.as_view(), name='export_commandes'),
    path('export/transporteurs/', views_api.ExportTransporteursView.as_view(), name='export_transporteurs'),
    path('reports/performance/', views_api.PerformanceReportView.as_view(), name='performance_report'),
    path('reports/financial/', views_api.FinancialReportView.as_view(), name='financial_report'),
    
    # Upload de fichiers
    path('upload/image/', views_api.ImageUploadView.as_view(), name='upload_image'),
    path('upload/document/', views_api.DocumentUploadView.as_view(), name='upload_document'),
    
    # Statistiques et métriques
    path('stats/overview/', views_api.OverviewStatsView.as_view(), name='overview_stats'),
    path('stats/commandes/', views_api.CommandeStatsView.as_view(), name='commande_stats'),
    path('stats/transporteurs/', views_api.TransporteurStatsView.as_view(), name='transporteur_stats'),
    path('stats/performance/', views_api.PerformanceStatsView.as_view(), name='performance_stats'),
    
    # Recherche avancée
    path('search/commandes/', views_api.SearchCommandesView.as_view(), name='search_commandes'),
    path('search/transporteurs/', views_api.SearchTransporteursView.as_view(), name='search_transporteurs'),
    path('search/clients/', views_api.SearchClientsView.as_view(), name='search_clients'),
    
    # Webhooks
    path('webhooks/tracking-update/', views_api.TrackingWebhookView.as_view(), name='tracking_webhook'),
    path('webhooks/payment-confirmation/', views_api.PaymentWebhookView.as_view(), name='payment_webhook'),
    
    # Configuration et paramètres
    path('config/', views_api.ConfigurationView.as_view(), name='configuration'),
    path('parametres/', views_api.ParametresView.as_view(), name='parametres'),
    path('parametres/<str:nom>/', views_api.ParametreDetailView.as_view(), name='parametre_detail'),
    
    # Monitoring et santé
    path('health/', views_api.HealthCheckView.as_view(), name='health_check'),
    path('metrics/', views_api.MetricsView.as_view(), name='metrics'),
]