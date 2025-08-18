"""
ASGI config for visitor_system project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

try:
    from django.core.asgi import get_asgi_application  # type: ignore  # pylint: disable=import-error
except ImportError:  # pragma: no cover
    # Локальная среда линтера без Django
    def get_asgi_application():  # type: ignore
        raise RuntimeError("Django is not available in the lint environment")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev'))

application = get_asgi_application()
