# api/urls.py - URLs API optimisées

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt import views as jwt_views
from .views import (
    ClientViewSet, TransporteurViewSet, CommandeViewSet,
    MissionViewSet, IncidentViewSet, NotificationViewSet
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'transporteurs', TransporteurViewSet, basename='transporteur')
router.register(r'commandes', CommandeViewSet, basename='commande')
router.register(r'missions', MissionViewSet, basename='mission')
router.register(r'incidents', IncidentViewSet, basename='incident')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # Endpoints API REST
    path('', include(router.urls)),
    
    # Authentification JWT
    path('auth/token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', jwt_views.TokenVerifyView.as_view(), name='token_verify'),
]