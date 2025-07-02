"""
Configuration Django pour le système de transport de marchandises
"""

from pathlib import Path
import os
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# Configuration de sécurité
SECRET_KEY = config('SECRET_KEY', default='django-insecure-transport-system-key-2024')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

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

# Base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
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

# Fichiers statiques
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

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
    'PAGE_SIZE': 20
}

# Configuration CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
]
CORS_ALLOW_CREDENTIALS = True

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