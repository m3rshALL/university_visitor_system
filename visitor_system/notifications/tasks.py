# notifications/tasks.py
from celery import shared_task
from .utils import send_visit_creation_notification

@shared_task
def send_visit_notification_task(visit_id, visit_kind):
    """Асинхронная задача для отправки email уведомления."""
    print(f"Запуск задачи отправки уведомления для {visit_kind} ID {visit_id}")
    send_visit_creation_notification(visit_id, visit_kind)

@shared_task
def simple_test(x, y):
    print(f"Running simple_test with {x}, {y}")
    return x + y