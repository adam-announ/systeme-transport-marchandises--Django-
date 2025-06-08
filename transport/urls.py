# transport/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('commandes/', views.liste_commandes, name='liste_commandes'),
    path('commande/creer/', views.creer_commande, name='creer_commande'),
    path('commande/<int:commande_id>/suivre/', views.suivre_commande, name='suivre_commande'),
    path('optimiser/', views.optimiser_itineraire, name='optimiser_itineraire'),
]