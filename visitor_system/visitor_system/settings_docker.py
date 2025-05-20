"""
Docker-specific Django settings for visitor_system project.
"""
import os
from pathlib import Path
from .settings import *  # Import all settings from the main settings file

# Override settings for Docker environment

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-b_2g0i5hh+p3k()3^_pgjz3#e9hpxk^ub(dm&+i^y=do=w-^p+')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost 127.0.0.1 [::1] app nginx').split(' ')

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'visitor_system_db'),
        'USER': os.environ.get('POSTGRES_USER', 'visitor_system_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'Sako2020'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Celery settings
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

# Redis settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get('CACHE_URL', f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', '6379')}/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50, "socket_connect_timeout": 5},
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
