from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CommandeViewSet, VehiculeViewSet, LivraisonViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'commandes', CommandeViewSet, basename='commande')
router.register(r'vehicules', VehiculeViewSet, basename='vehicule')
router.register(r'livraisons', LivraisonViewSet, basename='livraison')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]