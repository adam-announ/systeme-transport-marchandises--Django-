# backend/transport/api_urls.py - Version simplifiée
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
    path('transporteurs/disponibles/', api_views.TransporteursDisponiblesView.as_view(), name='transporteurs_disponibles'),
    
    # Planification et optimisation
    path('assignation-automatique/', api_views.assignation_automatique, name='assignation_automatique'),
    path('calculer-itineraire/', api_views.calculer_itineraire_api, name='calculer_itineraire'),
    
    # Monitoring et santé
    path('health/', api_views.HealthCheckView.as_view(), name='health_check'),
    path('metrics/', api_views.MetricsView.as_view(), name='metrics'),
]