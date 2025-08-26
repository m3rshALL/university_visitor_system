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


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_daily_visit_summary():
    """Отправляет ежедневную сводку по визитам"""
    from django.utils import timezone
    from datetime import timedelta
    from visitors.models import Visit, StudentVisit
    from django.contrib.auth.models import User, Group
    
    try:
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Статистика за вчера
        visits_count = Visit.objects.filter(entry_time__date=yesterday).count()
        student_visits_count = StudentVisit.objects.filter(entry_time__date=yesterday).count()
        
        active_visits = Visit.objects.filter(
            status='CHECKED_IN',
            exit_time__isnull=True
        ).count()
        active_student_visits = StudentVisit.objects.filter(
            status='CHECKED_IN',
            exit_time__isnull=True
        ).count()
        
        # Формируем сводку
        subject = f"Ежедневная сводка по визитам - {yesterday.strftime('%d.%m.%Y')}"
        message = f"""
Ежедневная сводка по визитам за {yesterday.strftime('%d.%m.%Y')}:

Визиты за день:
- Официальные визиты: {visits_count}
- Студенческие визиты: {student_visits_count}
- Всего за день: {visits_count + student_visits_count}

Текущие активные визиты:
- Официальные: {active_visits}
- Студенческие: {active_student_visits}
- Всего активных: {active_visits + active_student_visits}

Отчет сгенерирован автоматически.
        """
        
        # Отправляем администраторам и группе Security Notifications
        recipients = []
        
        # Администраторы
        admin_emails = User.objects.filter(
            is_staff=True, 
            is_active=True,
            email__isnull=False
        ).exclude(email='').values_list('email', flat=True)
        recipients.extend(admin_emails)
        
        # Группа безопасности
        try:
            security_group = Group.objects.get(name="Security Notifications")
            security_emails = security_group.user_set.filter(
                is_active=True,
                email__isnull=False
            ).exclude(email='').values_list('email', flat=True)
            recipients.extend(security_emails)
        except Group.DoesNotExist:
            pass
        
        recipients = list(set(recipients))  # Убираем дубликаты
        
        if recipients:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False
            )
            
            logger.info("Daily visit summary sent to %d recipients", len(recipients))
            return {
                'status': 'success',
                'recipients_count': len(recipients),
                'visits_count': visits_count,
                'student_visits_count': student_visits_count,
                'active_visits': active_visits + active_student_visits
            }
        else:
            logger.warning("No recipients found for daily visit summary")
            return {'status': 'no_recipients'}
            
    except Exception as e:
        logger.error("Error sending daily visit summary: %s", e)
        raise