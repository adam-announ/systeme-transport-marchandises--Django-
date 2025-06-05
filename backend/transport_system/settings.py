import os
import sys
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-#l$t!yb)3j%4kqkak+)s(1ljs_$6g)6etk09^v97l4ulxml^$j')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    # Celery apps (optionnels pour développement)
    'django_celery_beat',
    'django_celery_results',
    # Channels pour WebSocket (optionnel)
    'channels',
]

LOCAL_APPS = [
    'transport',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware personnalisé (optionnel)
    # 'transport.middleware.RequestLoggingMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'transport_system.wsgi.application'

# Configuration ASGI pour Channels (optionnel)
ASGI_APPLICATION = 'transport_system.asgi.application'

# Database - Configuration flexible
# PostgreSQL avec PostGIS pour production
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DB_NAME', default=BASE_DIR / 'db.sqlite3'),
    }
}

# Configuration PostgreSQL si les variables sont définies
if config('DB_NAME', default='') and config('DB_ENGINE', default='').startswith('django.contrib.gis'):
    DATABASES = {
        'default': {
            'ENGINE': config('DB_ENGINE', default='django.contrib.gis.db.backends.postgis'),
            'NAME': config('DB_NAME', default='transport_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'OPTIONS': {
                'charset': 'utf8',
            },
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Casablanca'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Dossiers statiques pour développement
if DEBUG:
    STATICFILES_DIRS = [
        BASE_DIR / 'static',
    ]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
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
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# Spectacular settings (pour la documentation API)
SPECTACULAR_SETTINGS = {
    'TITLE': 'TransportPro API',
    'DESCRIPTION': 'API pour le système de gestion de transport de marchandises',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Seulement en développement

# Cache configuration - Flexible selon l'environnement
REDIS_URL = config('REDIS_URL', default='')

if REDIS_URL and 'redis://' in REDIS_URL:
    # Configuration Redis si disponible
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
    
    # Channels configuration avec Redis
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [REDIS_URL],
            },
        },
    }
    
    # Celery configuration avec Redis
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = TIME_ZONE
    
    # Configuration des tâches périodiques
    CELERY_BEAT_SCHEDULE = {
        'update-traffic-data': {
            'task': 'transport.tasks.update_traffic_data',
            'schedule': 300.0,  # Toutes les 5 minutes
        },
        'update-weather-data': {
            'task': 'transport.tasks.update_weather_data',
            'schedule': 900.0,  # Toutes les 15 minutes
        },
        'cleanup-old-notifications': {
            'task': 'transport.tasks.cleanup_old_notifications',
            'schedule': 86400.0,  # Tous les jours
        },
    }
else:
    # Configuration de cache en mémoire pour développement
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    
    # Channels configuration en mémoire
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Email configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@transportpro.com')

# Google Maps API
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# Configuration des messages
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Sessions
SESSION_COOKIE_AGE = 3600  # 1 heure
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Logging configuration
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
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'transport': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Créer les dossiers nécessaires
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
os.makedirs(BASE_DIR / 'media', exist_ok=True)
os.makedirs(BASE_DIR / 'static', exist_ok=True)

# Configuration des fichiers uploadés
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880   # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Configuration personnalisée pour l'application
TRANSPORT_CONFIG = {
    'MAX_DISTANCE_KM': 1000,
    'DEFAULT_VEHICLE_SPEED_KMH': 60,
    'NOTIFICATION_RETENTION_DAYS': 30,
    'MAX_INCIDENTS_PER_COMMAND': 10,
    'AUTOMATIC_ASSIGNMENT_ENABLED': True,
    'REAL_TIME_TRACKING_ENABLED': True,
}

# Paramètres de géolocalisation
LOCATION_FIELD = {
    'map.provider': 'google',
    'map.zoom': 13,
    'search.provider': 'google',
    'provider.google.api': '//maps.google.com/maps/api/js?sensor=false',
    'provider.google.api_key': GOOGLE_MAPS_API_KEY,
    'provider.google.api_libraries': 'places',
}

# Configuration des webhooks
WEBHOOK_SETTINGS = {
    'CLIENT_NOTIFICATION_URL': config('CLIENT_WEBHOOK_URL', default=''),
    'TRANSPORTEUR_NOTIFICATION_URL': config('TRANSPORTEUR_WEBHOOK_URL', default=''),
    'TIMEOUT': 30,
    'RETRY_ATTEMPTS': 3,
}

# Configuration des SMS (optionnel)
SMS_SETTINGS = {
    'PROVIDER': config('SMS_PROVIDER', default='twilio'),
    'API_KEY': config('SMS_API_KEY', default=''),
    'API_SECRET': config('SMS_API_SECRET', default=''),
    'FROM_NUMBER': config('SMS_FROM_NUMBER', default=''),
}

# Configuration des notifications push
PUSH_NOTIFICATIONS_SETTINGS = {
    'FCM_API_KEY': config('FCM_API_KEY', default=''),
    'APNS_CERTIFICATE': config('APNS_CERTIFICATE', default=''),
}

# Configuration de monitoring et métriques
if not DEBUG:
    # Sentry pour le monitoring d'erreurs (optionnel)
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        
        sentry_dsn = config('SENTRY_DSN', default='')
        if sentry_dsn:
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[
                    DjangoIntegration(),
                    CeleryIntegration(),
                ],
                traces_sample_rate=0.1,
                send_default_pii=True
            )
    except ImportError:
        pass

# Configuration des API externes
EXTERNAL_APIS = {
    'GOOGLE_MAPS': {
        'API_KEY': GOOGLE_MAPS_API_KEY,
        'RATE_LIMIT': 1000,  # Requêtes par jour
    },
    'WEATHER_API': {
        'API_KEY': config('WEATHER_API_KEY', default=''),
        'BASE_URL': 'https://api.openweathermap.org/data/2.5',
    },
    'TRAFFIC_API': {
        'API_KEY': config('TRAFFIC_API_KEY', default=''),
        'BASE_URL': 'https://api.tomtom.com/traffic/services',
    },
}

# Configuration des tests
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
    
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]
    
    # Désactiver Celery pour les tests
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    
    # Cache en mémoire pour les tests
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }