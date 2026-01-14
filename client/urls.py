from django.urls import path
from . import views

app_name = 'client'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('nouvelle-commande/', views.nouvelle_commande, name='nouvelle_commande'),
    path('mes-commandes/', views.mes_commandes, name='mes_commandes'),
    path('commande/<uuid:commande_id>/', views.commande_detail, name='commande_detail'),
    path('suivi/<uuid:commande_id>/', views.suivi_commande, name='suivi_commande'),
    path('commande/<uuid:commande_id>/pdf/', views.telecharger_pdf, name='telecharger_pdf'),
    path('commande/<uuid:commande_id>/bon-livraison/', views.telecharger_bon_livraison, name='telecharger_bon_livraison'),
    path('commande/<uuid:commande_id>/message/', views.envoyer_message, name='envoyer_message'),
    
    # API
    path('api/commandes/', views.api_commandes, name='api_commandes'),
    path('api/suivi/<uuid:commande_id>/', views.api_suivi_commande, name='api_suivi_commande'),
]