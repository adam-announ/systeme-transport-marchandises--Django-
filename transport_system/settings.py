"""
Django settings for transport_system project.
Système de gestion de transport de marchandises
"""

import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuration de sécurité
SECRET_KEY = config('SECRET_KEY', default='django-insecure-transport-system-key-2024')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Applications installées
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # API REST
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'transport_system.wsgi.application'

# Configuration de la base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    # MongoDB (optionnel)
    'mongodb': {
        'ENGINE': 'djongo',
        'NAME': config('MONGO_DB_NAME', default='transport_mongo'),
        'CLIENT': {
            'host': config('MONGO_HOST', default='localhost'),
            'port': config('MONGO_PORT', default=27017, cast=int),
            'username': config('MONGO_USER', default=''),
            'password': config('MONGO_PASSWORD', default=''),
        }
    }
}

# Configuration Neo4j
NEO4J_CONFIG = {
    'URI': config('NEO4J_URI', default='bolt://localhost:7687'),
    'USERNAME': config('NEO4J_USER', default='neo4j'),
    'PASSWORD': config('NEO4J_PASSWORD', default='password'),
    'DATABASE': config('NEO4J_DATABASE', default='neo4j'),
}

# Configuration MongoDB (MongoEngine)
MONGODB_CONFIG = {
    'HOST': config('MONGO_HOST', default='localhost'),
    'PORT': config('MONGO_PORT', default=27017, cast=int),
    'DB': config('MONGO_DB_NAME', default='transport_mongo'),
    'USERNAME': config('MONGO_USER', default=''),
    'PASSWORD': config('MONGO_PASSWORD', default=''),
}

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
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

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
}

# Configuration CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
]
CORS_ALLOW_CREDENTIALS = True

# Configuration de sécurité
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

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
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Configuration d'authentification
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

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
}

# Variables d'environnement pour le déploiement
DEPLOYMENT_SETTINGS = {
    'ENVIRONMENT': config('ENVIRONMENT', default='development'),
    'VERSION': config('VERSION', default='1.0.0'),
    'BUILD_NUMBER': config('BUILD_NUMBER', default='local'),
    'DEPLOY_DATE': config('DEPLOY_DATE', default=''),
}