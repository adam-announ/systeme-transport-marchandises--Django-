from django.urls import path
from . import views

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('service/gestion-commandes/', views.gestion_commandes, name='gestion_commandes'),
    path('service/optimisation-tournees/', views.optimisation_tournees, name='optimisation_tournees'),
    path('service/suivi-temps-reel/', views.suivi_temps_reel, name='suivi_temps_reel'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
