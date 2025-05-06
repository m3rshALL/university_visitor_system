# visitor_system/celery.py
import os
from celery import Celery

# Установите переменную окружения DJANGO_SETTINGS_MODULE для celery.
# Замените 'visitor_system.settings' на ваш путь к settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_system.settings')

# Создаем экземпляр Celery
# 'visitor_system' - имя вашего проекта Django
app = Celery('visitor_system')

# Используем настройки Django для конфигурации Celery.
# Префикс 'CELERY_' в настройках Django.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически обнаруживать задачи в файлах tasks.py ваших приложений Django.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')