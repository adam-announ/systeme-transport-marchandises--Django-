# transport_system/urls.py - Version finale
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from transport import admin_views  # Import direct

def redirect_logout(request):
    return redirect('logout')

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    
    # Custom admin routes
    path('admin/dashboard/', admin_views.dashboard_admin, name='admin_dashboard'),
    path('admin/utilisateurs/', admin_views.gestion_utilisateurs, name='gestion_utilisateurs'),
    path('admin/roles/', admin_views.gestion_roles, name='gestion_roles'),
    path('admin/journal/', admin_views.journal_activite, name='journal_activite'),
    path('admin/parametres/', admin_views.parametres_systeme, name='parametres_systeme'),
    
    # Logout redirect
    path('accounts/logout/', redirect_logout),
    
    # Include transport urls
    path('', include('transport.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)