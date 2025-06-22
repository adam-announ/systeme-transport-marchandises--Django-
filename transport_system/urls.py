# transport_system/urls.py - CORRECTION COMPLÈTE
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def redirect_logout(request):
    return redirect('logout')

urlpatterns = [
    # IMPORTANT: Include transport urls BEFORE Django admin
    # pour éviter les conflits avec /admin/
    path('', include('transport.urls')),
    
    # API endpoints
    path('api/', include('api.urls')),
    
    # Django admin APRÈS nos URLs custom
    path('django-admin/', admin.site.urls),  # Changé de 'admin/' vers 'django-admin/'
    
    # Logout redirect
    path('accounts/logout/', redirect_logout),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)