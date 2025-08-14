# visitor_system/celery.py
import os
from celery import Celery  # type: ignore  # pylint: disable=import-error

# Устанавливаем модуль настроек из окружения (по умолчанию dev)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev'))

app = Celery('visitor_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
