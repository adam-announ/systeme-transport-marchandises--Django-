# transport/urls.py - Sans les URLs admin pour éviter les conflits
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # URLs publiques
    path('', views.index, name='index'),
    path('inscription/', views.inscription, name='inscription'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # URLs pour les commandes
    path('commandes/', views.liste_commandes, name='liste_commandes'),
    path('commande/creer/', views.creer_commande, name='creer_commande'),
    path('commande/<int:commande_id>/suivre/', views.suivre_commande, name='suivre_commande'),
    path('commande/<int:commande_id>/supprimer/', views.supprimer_commande, name='supprimer_commande'),
    path('rapport/', views.generer_rapport, name='generer_rapport'),
]