"""
Пример интеграции WebPush уведомлений в приложение visitors

Добавьте этот код в ваши views или signals для автоматической
отправки push-уведомлений при важных событиях.
"""

from notifications.utils import create_notification_with_webpush


def send_guest_arrival_notification(visit):
    """
    Отправляет WebPush уведомление сотруднику о прибытии гостя
    
    Добавьте вызов этой функции в visitors/views.py 
    в функцию check_in_guest или аналогичную
    """
    try:
        notification, webpush_result = create_notification_with_webpush(
            recipient=visit.employee,
            title=f"К Вам прибыл гость: {visit.guest.full_name}",
            message=f"Цель визита: {visit.purpose}. Время прибытия: {visit.entry_time.strftime('%H:%M')}",
            notification_type="guest_arrived",
            action_url=f"/visitors/visit/{visit.id}/",
            related_object_id=visit.id,
            related_object_type="visit",
            send_push=True
        )
        
        if webpush_result and webpush_result['success']:
            print(f"WebPush уведомление отправлено {webpush_result['sent_count']} устройствам")
        
        return notification
        
    except Exception as e:
        print(f"Ошибка отправки WebPush уведомления: {e}")
        return None


def send_visit_approval_notification(visit, approved=True):
    """
    Уведомление об одобрении/отклонении визита
    
    Используйте в административных функциях
    """
    try:
        if approved:
            title = "Визит одобрен"
            message = f"Ваш визит к {visit.employee.get_full_name()} одобрен"
            notification_type = "visit_approved"
        else:
            title = "Визит отклонен"
            message = f"Ваш визит к {visit.employee.get_full_name()} отклонен"
            notification_type = "visit_denied"
        
        # Отправляем уведомление регистратору визита
        notification, webpush_result = create_notification_with_webpush(
            recipient=visit.registered_by,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=f"/visitors/visit/{visit.id}/",
            related_object_id=visit.id,
            related_object_type="visit",
            send_push=True
        )
        
        return notification
        
    except Exception as e:
        print(f"Ошибка отправки уведомления об одобрении: {e}")
        return None


def send_booking_confirmation_notification(booking):
    """
    Уведомление о подтверждении бронирования аудитории
    
    Интеграция с classroom_book приложением
    """
    try:
        notification, webpush_result = create_notification_with_webpush(
            recipient=booking.user,
            title="Бронирование подтверждено",
            message=f"Аудитория {booking.classroom.name} забронирована на {booking.start_time.strftime('%d.%m.%Y %H:%M')}",
            notification_type="booking_confirmed",
            action_url="/classroom/my-bookings/",
            related_object_id=booking.id,
            related_object_type="booking",
            send_push=True
        )
        
        return notification
        
    except Exception as e:
        print(f"Ошибка отправки уведомления о бронировании: {e}")
        return None


# Пример интеграции через Django signals
"""
Добавьте этот код в visitors/signals.py:

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Visit
from .webpush_integration import send_guest_arrival_notification

@receiver(post_save, sender=Visit)
def visit_post_save(sender, instance, created, **kwargs):
    # Отправляем уведомление при регистрации прибытия гостя
    if instance.entry_time and not created:  # Обновление с установкой времени прибытия
        send_guest_arrival_notification(instance)
"""


# Пример массовой отправки уведомлений
def send_system_notification_to_all_staff(title, message):
    """
    Отправка системного уведомления всем сотрудникам
    
    Используйте для важных объявлений
    """
    from django.contrib.auth.models import User
    from notifications.utils import send_webpush_to_multiple_users
    
    try:
        # Получаем всех активных сотрудников
        staff_users = User.objects.filter(is_active=True, is_staff=True)
        
        result = send_webpush_to_multiple_users(
            users=staff_users,
            title=title,
            body=message,
            data={
                'type': 'system',
                'url': '/'
            }
        )
        
        print(f"Системное уведомление отправлено {result['sent_count']} сотрудникам")
        return result
        
    except Exception as e:
        print(f"Ошибка массовой отправки: {e}")
        return None


# Пример отправки напоминаний
def send_visit_reminders():
    """
    Отправка напоминаний о предстоящих визитах
    
    Можно запускать через Celery задачу
    """
    from datetime import datetime, timedelta
    from visitors.models import Visit
    
    try:
        # Находим визиты на завтра
        tomorrow = datetime.now().date() + timedelta(days=1)
        upcoming_visits = Visit.objects.filter(
            expected_entry_time__date=tomorrow,
            entry_time__isnull=True  # Еще не прибыл
        )
        
        for visit in upcoming_visits:
            create_notification_with_webpush(
                recipient=visit.employee,
                title="Напоминание о визите",
                message=f"Завтра к Вам придет {visit.guest.full_name} в {visit.expected_entry_time.strftime('%H:%M')}",
                notification_type="visit_reminder",
                action_url=f"/visitors/visit/{visit.id}/",
                related_object_id=visit.id,
                related_object_type="visit",
                send_push=True
            )
        
        print(f"Отправлено {len(upcoming_visits)} напоминаний")
        
    except Exception as e:
        print(f"Ошибка отправки напоминаний: {e}")
