# backend/transport_system/wsgi.py
"""
WSGI config for transport_system project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')

application = get_wsgi_application()

