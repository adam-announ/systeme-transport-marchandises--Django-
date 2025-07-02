"""
URLs principales du système de transport
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def home_redirect(request):
    """Redirection vers la page de connexion"""
    return redirect('auth:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_redirect, name='home'),
    
    # Applications
    path('auth/', include('authentication.urls')),
    path('client/', include('client.urls')),
    path('admin-panel/', include('admin_panel.urls')),
    path('planificateur/', include('planificateur.urls')),
    path('transporteur/', include('transporteur.urls')),
]