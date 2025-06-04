# Remplacer le contenu de backend/transport/apps.py par:

from django.apps import AppConfig


class TransportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transport'
    verbose_name = 'Transport Management'
    
    def ready(self):
        # Import des signaux si nécessaire
        pass