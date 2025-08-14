"""
Development settings for visitor_system project.
"""
from .base import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['10.1.10.206', '127.0.0.1', 'localhost', '.ngrok-free.app']

INTERNAL_IPS = [
    '127.0.0.1',
]

# CSRF Configuration for development
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://*.ngrok-free.app',
]

# Development-specific CSRF/HTTPS settings
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Use HTTPS settings only if behind a proxy (like ngrok)
if os.environ.get('USE_HTTPS_PROXY', 'False').lower() == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# Database for development (use localhost unless in Docker)
if os.environ.get('IN_DOCKER', 'False').lower() == 'true':
    DATABASES['default']['HOST'] = 'db'
else:
    DATABASES['default']['HOST'] = 'localhost'

# Development PWA settings
PWA_DEBUG = DEBUG