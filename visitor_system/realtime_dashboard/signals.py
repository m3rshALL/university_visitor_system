# realtime_dashboard/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from visitors.models import Visit, StudentVisit
from .services import event_service
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Visit)
def handle_visit_events(sender, instance, created, **kwargs):
    """Обработка событий визитов"""
    try:
        if created:
            # Новый визит создан
            event_service.notify_visit_created(instance)
        else:
            # Визит обновлен - проверяем изменения статуса
            if instance.status == 'CHECKED_IN' and instance.entry_time:
                event_service.notify_visit_checked_in(instance)
            elif instance.status == 'CHECKED_OUT' and instance.exit_time:
                event_service.notify_visit_checked_out(instance)
    except Exception as e:
        logger.error(f"Error handling visit event: {e}")


@receiver(post_save, sender=StudentVisit)
def handle_student_visit_events(sender, instance, created, **kwargs):
    """Обработка событий студенческих визитов"""
    try:
        if created:
            # Новый студенческий визит создан
            event_service.create_event(
                event_type='visit_created',
                title='Новый визит студента',
                message=f'Студент {instance.guest.full_name} зарегистрирован для посещения {instance.department.name}',
                priority='normal',
                data={
                    'visit_type': 'student',
                    'guest_name': instance.guest.full_name,
                    'department': instance.department.name
                }
            )
        else:
            # Студенческий визит обновлен
            if instance.status == 'CHECKED_IN' and instance.entry_time:
                event_service.create_event(
                    event_type='visit_checked_in',
                    title='Студент вошел в здание',
                    message=f'Студент {instance.guest.full_name} вошел в здание',
                    priority='normal',
                    data={
                        'visit_type': 'student',
                        'guest_name': instance.guest.full_name,
                        'entry_time': instance.entry_time.isoformat() if instance.entry_time else None
                    }
                )
            elif instance.status == 'CHECKED_OUT' and instance.exit_time:
                event_service.create_event(
                    event_type='visit_checked_out',
                    title='Студент покинул здание',
                    message=f'Студент {instance.guest.full_name} покинул здание',
                    priority='normal',
                    data={
                        'visit_type': 'student',
                        'guest_name': instance.guest.full_name,
                        'exit_time': instance.exit_time.isoformat() if instance.exit_time else None
                    }
                )
    except Exception as e:
        logger.error(f"Error handling student visit event: {e}")
