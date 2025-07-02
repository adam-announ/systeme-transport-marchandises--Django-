"""
URLs pour l'interface administrateur
"""

from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('utilisateurs/', views.gestion_utilisateurs, name='gestion_utilisateurs'),
    path('utilisateurs/creer/', views.creer_utilisateur, name='creer_utilisateur'),
    path('utilisateurs/modifier/<uuid:user_id>/', views.modifier_utilisateur, name='modifier_utilisateur'),
    path('commandes/', views.gestion_commandes, name='gestion_commandes'),
    path('journal/', views.journal_activite, name='journal_activite'),
    path('configuration/', views.configuration_systeme, name='configuration_systeme'),
    path('notification/', views.envoyer_notification, name='envoyer_notification'),
    path('rapports/', views.rapports, name='rapports'),
    
    # API
    path('api/statistiques/', views.api_statistiques, name='api_statistiques'),
    path('api/utilisateurs/<uuid:user_id>/supprimer/', views.api_supprimer_utilisateur, name='api_supprimer_utilisateur'),
]