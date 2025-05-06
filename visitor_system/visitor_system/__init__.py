# visitor_system/__init__.py

# Этот код гарантирует, что @shared_task будет использовать это приложение Celery.
from .celery import app as celery_app

__all__ = ('celery_app',)