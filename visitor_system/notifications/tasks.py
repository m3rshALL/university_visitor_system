# notifications/tasks.py
from celery import shared_task
from .utils import send_visit_creation_notification
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_visit_notification_task(visit_id, visit_kind):
    """Асинхронная задача для отправки email уведомления."""
    print(f"Запуск задачи отправки уведомления для {visit_kind} ID {visit_id}")
    send_visit_creation_notification(visit_id, visit_kind)

@shared_task
def simple_test(x, y):
    print(f"Running simple_test with {x}, {y}")
    return x + y

@shared_task
def send_exit_notification(recipient_email, subject, message):
    """
    Асинхронно отправляет уведомление о выходе посетителя.
    
    Args:
        recipient_email (str): Email адрес получателя
        subject (str): Тема письма
        message (str): Текст письма
    Returns:
        bool: Успех или неудача отправки
    """
    try:
        logger.info(f"Отправка уведомления о выходе на {recipient_email}")
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        logger.info(f"Уведомление о выходе успешно отправлено на {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о выходе: {e}")
        return False