"""
URLs principales du système de transport
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

def home_redirect(request):
    """Redirection vers la page de connexion"""
    return redirect('auth:login')

@login_required
def api_notifications_count(request):
    from core.models import Notification
    count = Notification.objects.filter(utilisateur=request.user, lue=False).count()
    return JsonResponse({'count': count})

@login_required
def api_notifications_list(request):
    from core.models import Notification
    notifications = Notification.objects.filter(utilisateur=request.user).order_by('-date_creation')[:10]
    data = [{
        'id': str(n.id),
        'titre': n.titre,
        'message': n.message,
        'type_notification': n.type_notification,
        'lue': n.lue,
        'date_creation': n.date_creation.isoformat()
    } for n in notifications]
    return JsonResponse({'notifications': data})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_redirect, name='home'),
    
    # API Notifications
    path('api/notifications/count/', api_notifications_count, name='api_notifications_count'),
    path('api/notifications/', api_notifications_list, name='api_notifications_list'),
    
    # Applications
    path('auth/', include('authentication.urls')),
    path('client/', include('client.urls')),
    path('admin-panel/', include('admin_panel.urls')),
    path('planificateur/', include('planificateur.urls')),
    path('transporteur/', include('transporteur.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0]) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)