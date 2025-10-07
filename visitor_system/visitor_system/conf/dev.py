from .base import *  # noqa

# Dev overrides
DEBUG = True
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Отключаем SSL редирект в dev
SECURE_SSL_REDIRECT = False

# Для ngrok: разрешаем все домены в режиме разработки
ALLOWED_HOSTS = ['*']

# Отключаем некоторые проверки безопасности для ngrok
CSRF_COOKIE_SAMESITE = None
SESSION_COOKIE_SAMESITE = None

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


