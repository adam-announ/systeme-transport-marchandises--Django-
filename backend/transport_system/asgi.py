# backend/transport_system/asgi.py
"""
ASGI config for transport_system project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')

application = get_asgi_application()