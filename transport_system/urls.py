from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/', include('utilisateurs.api_urls')),
    path('', include('utilisateurs.urls')),
    path('maps/', include('utilisateurs.urls_google_maps')),
]
