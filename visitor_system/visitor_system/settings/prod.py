"""
Production settings for visitor_system project.
"""
from .base import *
import os

# Security settings for production
DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Security headers and HTTPS enforcement
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Secure cookies
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

# CSRF trusted origins for production
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

# Database for production (use environment or Docker host)
DATABASES['default']['HOST'] = os.environ.get('POSTGRES_HOST', 'db')

# Production logging - output to stdout/stderr for Docker
LOGGING['handlers']['console']['level'] = 'INFO'
LOGGING['handlers']['file']['level'] = 'WARNING'

# Remove file logging in production to use centralized logging
del LOGGING['handlers']['file']
for logger_config in LOGGING['loggers'].values():
    if 'file' in logger_config.get('handlers', []):
        logger_config['handlers'] = [h for h in logger_config['handlers'] if h != 'file']

# Production PWA settings
PWA_DEBUG = False

# Security middleware additions for production
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_FONT_SRC = ("'self'", "data:")
CSP_IMG_SRC = ("'self'", "data:")

# Rate limiting (to be configured in Nginx)
# Session configuration for production
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Cache configuration for production
CACHES['default']['LOCATION'] = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', '6379')}/1"