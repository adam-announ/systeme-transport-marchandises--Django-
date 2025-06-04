# transport/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import api_views

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'commandes', api_views.CommandeViewSet, basename='commande')
router.register(r'transporteurs', api_views.TransporteurViewSet, basename='transporteur')
router.register(r'clients', api_views.ClientViewSet, basename='client')
router.register(r'incidents', api_views.IncidentViewSet, basename='incident')
router.register(r'notifications', api_views.NotificationViewSet, basename='notification')
router.register(r'journal', api_views.JournalViewSet, basename='journal')

urlpatterns = [
    # Authentification
    path('auth/login/', api_views.LoginView.as_view(), name='api_login'),
    path('auth/logout/', api_views.LogoutView.as_view(), name='api_logout'),
    path('auth/register/', api_views.RegisterView.as_view(), name='api_register'),
    path('auth/user/', api_views.CurrentUserView.as_view(), name='current_user'),
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    path('auth/refresh/', api_views.RefreshTokenView.as_view(), name='refresh_token'),
    
    # Endpoints du router
    path('', include(router.urls)),
    
    # Endpoints personnalisés
    path('dashboard/', api_views.dashboard_data, name='dashboard_data'),
    path('dashboard/client/', api_views.ClientDashboardView.as_view(), name='client_dashboard_api'),
    path('dashboard/transporteur/', api_views.TransporteurDashboardView.as_view(), name='transporteur_dashboard_api'),
    path('dashboard/admin/', api_views.AdminDashboardView.as_view(), name='admin_dashboard_api'),
    path('dashboard/planificateur/', api_views.PlanificateurDashboardView.as_view(), name='planificateur_dashboard_api'),
    
    # Gestion des commandes
    path('commandes/<uuid:pk>/assigner-transporteur/', api_views.AssignTransporteurView.as_view(), name='assign_transporteur'),
    path('commandes/<uuid:pk>/changer-statut/', api_views.ChangeStatusView.as_view(), name='change_status'),
    path('commandes/<uuid:pk>/tracking/', api_views.TrackingListView.as_view(), name='commande_tracking'),
    path('commandes/<uuid:pk>/bon-livraison/', api_views.BonLivraisonView.as_view(), name='bon_livraison'),
    
    # Gestion des transporteurs
    path('transporteurs/<int:pk>/toggle-disponibilite/', api_views.ToggleDisponibiliteView.as_view(), name='toggle_disponibilite'),
    path('transporteurs/<int:pk>/position/', api_views.UpdatePositionView.as_view(), name='update_position'),
    path('transporteurs/disponibles/', api_views.TransporteursDisponiblesView.as_view(), name='transporteurs_disponibles'),
    
    # Planification et optimisation
    path('assignation-automatique/', api_views.assignation_automatique, name='assignation_automatique'),
    path('optimiser-itineraires/', api_views.OptimiserItinerairesView.as_view(), name='optimiser_itineraires'),
    path('calculer-itineraire/', api_views.calculer_itineraire_api, name='calculer_itineraire'),
    
    # Géolocalisation et cartes
    path('geocoding/', api_views.GeocodingView.as_view(), name='geocoding'),
    path('reverse-geocoding/', api_views.ReverseGeocodingView.as_view(), name='reverse_geocoding'),
    path('traffic-info/', api_views.TrafficInfoView.as_view(), name='traffic_info'),
    path('weather-info/', api_views.WeatherInfoView.as_view(), name='weather_info'),
    
    # Rapports et exports
    path('export/commandes/', api_views.ExportCommandesView.as_view(), name='export_commandes'),
    path('export/transporteurs/', api_views.ExportTransporteursView.as_view(), name='export_transporteurs'),
    path('reports/performance/', api_views.PerformanceReportView.as_view(), name='performance_report'),
    path('reports/financial/', api_views.FinancialReportView.as_view(), name='financial_report'),
    
    # Upload de fichiers
    path('upload/image/', api_views.ImageUploadView.as_view(), name='upload_image'),
    path('upload/document/', api_views.DocumentUploadView.as_view(), name='upload_document'),
    
    # Statistiques et métriques
    path('stats/overview/', api_views.OverviewStatsView.as_view(), name='overview_stats'),
    path('stats/commandes/', api_views.CommandeStatsView.as_view(), name='commande_stats'),
    path('stats/transporteurs/', api_views.TransporteurStatsView.as_view(), name='transporteur_stats'),
    path('stats/performance/', api_views.PerformanceStatsView.as_view(), name='performance_stats'),
    
    # Recherche avancée
    path('search/commandes/', api_views.SearchCommandesView.as_view(), name='search_commandes'),
    path('search/transporteurs/', api_views.SearchTransporteursView.as_view(), name='search_transporteurs'),
    path('search/clients/', api_views.SearchClientsView.as_view(), name='search_clients'),
    
    # Webhooks
    path('webhooks/tracking-update/', api_views.TrackingWebhookView.as_view(), name='tracking_webhook'),
    path('webhooks/payment-confirmation/', api_views.PaymentWebhookView.as_view(), name='payment_webhook'),
    
    # Configuration et paramètres
    path('config/', api_views.ConfigurationView.as_view(), name='configuration'),
    path('parametres/', api_views.ParametresView.as_view(), name='parametres'),
    path('parametres/<str:nom>/', api_views.ParametreDetailView.as_view(), name='parametre_detail'),
    
    # Monitoring et santé
    path('health/', api_views.HealthCheckView.as_view(), name='health_check'),
    path('metrics/', api_views.MetricsView.as_view(), name='metrics'),
]