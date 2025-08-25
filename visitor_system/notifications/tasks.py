from celery import shared_task
from .utils import send_visit_creation_notification
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_visit_notification_task(visit_id, visit_kind):
    """Асинхронная задача для отправки email уведомления."""
    logger.info("Запуск задачи отправки уведомления для %s ID %s", visit_kind, visit_id)
    send_visit_creation_notification(visit_id, visit_kind)

@shared_task
def simple_test(x, y):
    logger.info("Running simple_test with %s, %s", x, y)
    return x + y

@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
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
        logger.info("Отправка уведомления о выходе на %s", recipient_email)
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        logger.info("Уведомление о выходе успешно отправлено на %s", recipient_email)
        return True
    except Exception as e:
        logger.error("Ошибка при отправке уведомления о выходе: %s", e)
        raise