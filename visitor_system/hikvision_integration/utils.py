"""
Utility функции для HikVision/HikCentral интеграции.

Включает функции для:
- Отправки security alerts
- Форматирования данных
- Вспомогательные утилиты
"""

import logging
from typing import Optional
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_security_alert_async(incident_id: int):
    """
    Асинхронная отправка security alert для инцидента.
    
    Запускает Celery task для отправки email/SMS уведомлений
    администраторам безопасности.
    
    Args:
        incident_id: ID SecurityIncident
    """
    try:
        from .tasks import send_security_alert_task
        send_security_alert_task.apply_async(
            args=[incident_id],
            countdown=5  # Задержка 5 секунд
        )
        logger.info(f"Security alert task scheduled for incident {incident_id}")
    except Exception as e:
        logger.error(f"Failed to schedule security alert task: {e}")
        # Fallback: пытаемся отправить синхронно
        try:
            send_security_alert_sync(incident_id)
        except Exception as sync_exc:
            logger.error(f"Failed to send security alert sync: {sync_exc}")


def send_security_alert_sync(incident_id: int):
    """
    Синхронная отправка security alert.
    
    Используется как fallback если Celery недоступен.
    
    Args:
        incident_id: ID SecurityIncident
    """
    try:
        from visitors.models import SecurityIncident
        
        incident = SecurityIncident.objects.select_related(
            'visit__guest', 'visit__employee', 'visit__department'
        ).get(id=incident_id)
        
        # Проверяем, не был ли уже отправлен alert
        if incident.alert_sent:
            logger.info(f"Alert for incident {incident_id} already sent, skipping")
            return
        
        # Получаем список администраторов безопасности
        security_admins = _get_security_admin_emails()
        
        if not security_admins:
            logger.warning("No security admins configured, skipping alert")
            return
        
        # Формируем тему и текст email
        subject = f'🚨 Security Alert: {incident.get_incident_type_display()}'
        
        context = {
            'incident': incident,
            'visit': incident.visit,
            'guest': incident.visit.guest,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        # HTML email
        html_message = render_to_string('notifications/email/security_alert.html', context)
        
        # Plain text fallback
        plain_message = f"""
SECURITY ALERT

Тип инцидента: {incident.get_incident_type_display()}
Уровень важности: {incident.get_severity_display()}
Статус: {incident.get_status_display()}

Гость: {incident.visit.guest.full_name}
Принимающий: {incident.visit.employee.get_full_name() if incident.visit.employee else 'N/A'}
Департамент: {incident.visit.department.name if incident.visit.department else 'N/A'}

Описание:
{incident.description}

Время обнаружения: {incident.detected_at.strftime('%Y-%m-%d %H:%M:%S')}

---
Автоматическое уведомление от системы учета посетителей
"""
        
        # Отправляем email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=security_admins,
            html_message=html_message,
            fail_silently=False,
        )
        
        # Обновляем incident
        incident.alert_sent = True
        incident.alert_sent_at = timezone.now()
        incident.save(update_fields=['alert_sent', 'alert_sent_at'])
        
        logger.info(
            f"Security alert sent for incident {incident_id} "
            f"to {len(security_admins)} recipients"
        )
        
    except Exception as e:
        logger.error(f"Failed to send security alert for incident {incident_id}: {e}")
        import traceback
        traceback.print_exc()


def _get_security_admin_emails() -> list[str]:
    """
    Получает список email адресов администраторов безопасности.
    
    Returns:
        Список email адресов
    """
    # Получаем из settings
    security_emails = getattr(settings, 'SECURITY_ADMIN_EMAILS', [])
    
    if security_emails:
        return security_emails
    
    # Fallback: используем ADMINS
    from django.conf import settings as django_settings
    admins = getattr(django_settings, 'ADMINS', [])
    
    if admins:
        return [email for name, email in admins]
    
    # Последний fallback: суперпользователи
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        superusers = User.objects.filter(
            is_superuser=True,
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        return list(superusers.values_list('email', flat=True))
    except Exception as e:
        logger.error(f"Failed to get superuser emails: {e}")
        return []


def format_duration(seconds: float) -> str:
    """
    Форматирует продолжительность в читаемый вид.
    
    Args:
        seconds: Количество секунд
        
    Returns:
        Строка вида "2 ч 30 мин" или "45 мин"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if hours > 0:
        return f"{hours} ч {minutes} мин"
    else:
        return f"{minutes} мин"


def get_work_hours() -> tuple[int, int]:
    """
    Получает рабочие часы из settings.
    
    Returns:
        Кортеж (start_hour, end_hour)
    """
    start = getattr(settings, 'WORK_HOURS_START', 6)
    end = getattr(settings, 'WORK_HOURS_END', 22)
    return start, end


def is_work_hours(dt: Optional[timezone.datetime] = None) -> bool:
    """
    Проверяет, находится ли время в рабочих часах.
    
    Args:
        dt: Дата/время для проверки (если None, используется текущее время)
        
    Returns:
        True если в рабочих часах, иначе False
    """
    if dt is None:
        dt = timezone.now()
    
    start, end = get_work_hours()
    hour = dt.hour
    
    return start <= hour < end

