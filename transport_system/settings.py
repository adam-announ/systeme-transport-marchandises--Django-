"""
Configuration Django améliorée pour le système de transport de marchandises
"""

from pathlib import Path
import os
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# Configuration de sécurité
SECRET_KEY = config('SECRET_KEY', default='django-insecure-transport-system-key-2024')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Applications installées
INSTALLED_APPS = [
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'transport_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.global_settings',  # Contexte global personnalisé
            ],
        },
    },
]

WSGI_APPLICATION = 'transport_system.wsgi.application'
ASGI_APPLICATION = 'transport_system.asgi.application'

# Configuration des bases de données
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    # Production avec PostgreSQL
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Développement avec SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Configuration Redis pour le cache et Celery
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Configuration des canaux WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# Configuration Celery pour les tâches asynchrones
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Paris'

# Validation des mots de passe
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalisation
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Fichiers statiques et médias
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Configuration WhiteNoise pour les fichiers statiques
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Modèle utilisateur personnalisé
AUTH_USER_MODEL = 'core.User'

# Configuration des APIs externes
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')
OPENWEATHER_API_KEY = config('OPENWEATHER_API_KEY', default='')
OPENROUTE_API_KEY = config('OPENROUTE_API_KEY', default='')

# Configuration REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# Configuration CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "https://transport-system.com",
]
CORS_ALLOW_CREDENTIALS = True

# Configuration de sécurité
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Configuration Email
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@transport-system.com')

# Configuration des logs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'transport_system.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'transport_system': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Créer le dossier logs s'il n'existe pas
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Configuration des rôles utilisateur
USER_ROLES = {
    'CLIENT': 'client',
    'ADMIN': 'admin',
    'PLANIFICATEUR': 'planificateur',
    'TRANSPORTEUR': 'transporteur',
}

# Configuration des statuts de commande
ORDER_STATUS = {
    'EN_ATTENTE': 'en_attente',
    'CONFIRMEE': 'confirmee',
    'EN_COURS': 'en_cours',
    'LIVREE': 'livree',
    'ANNULEE': 'annulee',
    'RETOURNEE': 'retournee',
    'INCIDENT': 'incident',
}

# Configuration de la géolocalisation
DEFAULT_COORDINATES = {
    'CASABLANCA': {'lat': 33.5731, 'lng': -7.5898},
    'RABAT': {'lat': 34.0209, 'lng': -6.8416},
    'MARRAKECH': {'lat': 31.6295, 'lng': -7.9811},
}

# Configuration du système de tarification
TARIFICATION = {
    'TARIF_BASE_KM': 0.8,  # MAD par km
    'TARIF_BASE_POIDS': 2.0,  # MAD par kg
    'TARIF_BASE_VOLUME': 5.0,  # MAD par m³
    'COEFFICIENT_URGENCE': 1.5,
    'COEFFICIENT_EXPRESS': 2.0,
    'COEFFICIENT_WEEKEND': 1.2,
    'COEFFICIENT_NUIT': 1.3,
}

# Configuration des notifications
NOTIFICATION_SETTINGS = {
    'SEND_EMAIL_NOTIFICATIONS': config('SEND_EMAIL_NOTIFICATIONS', default=True, cast=bool),
    'SEND_SMS_NOTIFICATIONS': config('SEND_SMS_NOTIFICATIONS', default=False, cast=bool),
    'REAL_TIME_TRACKING': config('REAL_TIME_TRACKING', default=True, cast=bool),
    'TRACKING_INTERVAL_SECONDS': config('TRACKING_INTERVAL_SECONDS', default=30, cast=int),
}

# Configuration des limites système
SYSTEM_LIMITS = {
    'MAX_COMMANDES_PAR_TOURNEE': 20,
    'MAX_DISTANCE_TOURNEE_KM': 500,
    'MAX_DUREE_TOURNEE_HEURES': 12,
    'MAX_POIDS_VEHICULE_KG': 44000,
    'MAX_VOLUME_VEHICULE_M3': 100,
}

# Configuration des APIs de mapping
MAPPING_APIS = {
    'GOOGLE_MAPS': {
        'ENABLED': bool(GOOGLE_MAPS_API_KEY),
        'API_KEY': GOOGLE_MAPS_API_KEY,
        'MAX_REQUESTS_PER_DAY': 25000,
    },
    'OPENROUTE': {
        'ENABLED': bool(OPENROUTE_API_KEY),
        'API_KEY': OPENROUTE_API_KEY,
        'MAX_REQUESTS_PER_DAY': 2000,
    },
}

# Configuration de la surveillance système
MONITORING = {
    'HEALTH_CHECK_ENABLED': config('HEALTH_CHECK_ENABLED', default=True, cast=bool),
    'METRICS_ENABLED': config('METRICS_ENABLED', default=True, cast=bool),
    'ERROR_REPORTING_ENABLED': config('ERROR_REPORTING_ENABLED', default=True, cast=bool),
}

# Configuration des tâches périodiques Celery
CELERY_BEAT_SCHEDULE = {
    'optimiser-tournees-quotidiennes': {
        'task': 'planificateur.tasks.optimiser_tournees_quotidiennes',
        'schedule': 60.0 * 60.0,  # Chaque heure
    },
    'mise-a-jour-positions': {
        'task': 'transporteur.tasks.mettre_a_jour_positions',
        'schedule': 30.0,  # Toutes les 30 secondes
    },
    'nettoyage-donnees': {
        'task': 'core.tasks.nettoyer_donnees_anciennes',
        'schedule': 60.0 * 60.0 * 24.0,  # Quotidien
    },
    'rapports-automatiques': {
        'task': 'admin_panel.tasks.generer_rapports_automatiques',
        'schedule': 60.0 * 60.0 * 24.0,  # Quotidien
    },
}

# Configuration de développement spécifique
if DEBUG:
    # Outils de debug
    INSTALLED_APPS += [
        'debug_toolbar',
    ]
    
    MIDDLEWARE += [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ]
    
    INTERNAL_IPS = [
        '127.0.0.1',
    ]
    
    # Configuration de la toolbar de debug
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }

# Variables d'environnement pour le déploiement
DEPLOYMENT_SETTINGS = {
    'ENVIRONMENT': config('ENVIRONMENT', default='development'),
    'VERSION': config('VERSION', default='1.0.0'),
    'BUILD_NUMBER': config('BUILD_NUMBER', default='local'),
    'DEPLOY_DATE': config('DEPLOY_DATE', default=''),
}
admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # Pour les fonctionnalités géospatiales
    
    # API REST et WebSocket
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'channels',
    
    # Outils de développement
    'django_extensions',
    
    # Applications du système de transport
    'core',
    'authentication',
    'client',
    'admin_panel',
    'planificateur',
    'transporteur',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Pour les fichiers statiques
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.
]