from .base import *  # noqa

# Dev overrides
DEBUG = True
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


