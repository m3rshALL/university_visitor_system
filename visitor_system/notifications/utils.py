import logging
from django.conf import settings
from django.template.loader import render_to_string  # Для HTML писем (опционально)
from django.template import TemplateDoesNotExist
from django.core.mail import send_mail, BadHeaderError
from django.contrib.auth.models import User, Group  # Добавляем Group
from django.db import DatabaseError
from django.utils import timezone
from smtplib import SMTPException
import json

# WebPush imports
try:
    from webpush import send_user_notification
    from webpush.models import PushInformation
except ImportError:
    send_user_notification = None
    PushInformation = None

try:
    from prometheus_client import Counter 
    EMAIL_SEND_TOTAL = Counter('email_send_total', 'Total email send attempts', ['kind'])
    EMAIL_SEND_FAILURES = Counter('email_send_failures_total', 'Total email send failures', ['kind'])
    WEBPUSH_SEND_TOTAL = Counter('webpush_send_total', 'Total webpush send attempts')
    WEBPUSH_SEND_FAILURES = Counter('webpush_send_failures_total', 'Total webpush send failures')
except Exception:
    EMAIL_SEND_TOTAL = None
    EMAIL_SEND_FAILURES = None
    WEBPUSH_SEND_TOTAL = None
    WEBPUSH_SEND_FAILURES = None

# Имя группы, члены которой будут получать уведомления о регистрации визитов
SECURITY_NOTIFICATION_GROUP_NAME = "Security Notifications"  # Убедитесь, что это имя совпадает с созданным в админке

# Импортируем нужные модели из приложения visitors
try:
    from visitors.models import Visit, StudentVisit
except ImportError:
    logging.getLogger(__name__).error(
        "CRITICAL: Could not import models from visitors app in notifications.utils!"
    )
# -------------------------------------

logger = logging.getLogger(__name__)

def send_guest_arrival_email(visit):
    """Отправляет email уведомление принимающему сотруднику о прибытии гостя."""
    employee = visit.employee
    guest = visit.guest

    if not employee.email:
        logger.warning(
            "Не удалось отправить уведомление: у сотрудника %s нет email.",
            employee.username,
        )
        return False

    subject = f"К Вам прибыл гость: {guest.full_name}"
    message = (
        f"Уважаемый(ая) {employee.get_full_name() or employee.username},\n\n"
        f"К Вам прибыл гость: {guest.full_name}.\n"
        f"Цель визита: {visit.purpose}\n"
        f"Департамент: {visit.department.name}\n"
        f"Время прибытия: {visit.entry_time.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Гостя зарегистрировал: {visit.registered_by.get_full_name() or visit.registered_by.username}\n\n"
        f"Система пропусков Университета."
    )
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [employee.email]

    try:
        # Для HTML писем:
        # html_message = render_to_string('notifications/guest_arrival_email.html', {'visit': visit})
        # send_mail(subject, message, from_email, recipient_list, fail_silently=False, html_message=html_message)

        # Простое текстовое письмо:
        if EMAIL_SEND_TOTAL:
            EMAIL_SEND_TOTAL.labels(kind='guest_arrival').inc()
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

        logger.info(
            "Уведомление о прибытии гостя %s отправлено сотруднику %s",
            guest.full_name,
            employee.email,
        )
        return True
    except (BadHeaderError, SMTPException) as exc:
        if EMAIL_SEND_FAILURES:
            EMAIL_SEND_FAILURES.labels(kind='guest_arrival').inc()
        logger.error(
            "Ошибка отправки email уведомления сотруднику %s: %s",
            employee.email,
            exc,
            exc_info=True,
        )
        # В реальном проекте здесь лучше использовать асинхронные задачи (Celery)
        # чтобы ошибка отправки не влияла на основной процесс регистрации
        return False

def send_visit_creation_notification(visit_id, visit_kind):
    """Отправляет email уведомление о создании визита директору и хосту."""
    logger.info(
        "Attempting to send creation notification for %s ID %s",
        visit_kind,
        visit_id,
    )
    try:
        if visit_kind == 'official':
            # Добавляем select_related для связанных полей в email шаблоне
            visit = Visit.objects.select_related(
                'guest', 'employee', 'department', 'registered_by', 'department__director'
            ).get(pk=visit_id)
            host_employee = visit.employee
        elif visit_kind == 'student':
             # Студенческие визиты сейчас не отправляют уведомлений по этой логике
             # Но если бы отправляли, код был бы здесь:
             # visit = StudentVisit.objects.select_related(...).get(pk=visit_id)
             # host_employee = None
            logger.info(
                "Notification skipped for StudentVisit ID %s as per current logic.",
                visit_id,
            )
            return True # Считаем успешным, т.к. не должны были отправлять
        else:
            logger.error(
                "Unknown visit_kind '%s' for notification (ID: %s)",
                visit_kind,
                visit_id,
            )
            return False
    except (Visit.DoesNotExist, StudentVisit.DoesNotExist):
        logger.error(
            "Visit %s with ID %s not found for sending notification.",
            visit_kind,
            visit_id,
        )
        return False
    except (DatabaseError, ValueError, TypeError) as exc:
        logger.exception(
            "Error fetching visit object %s ID %s for notification: %s",
            visit_kind,
            visit_id,
            exc,
        )
        return False

    recipients = set()
    log_recipients = [] # Для лога

    # Добавляем хоста
    if host_employee and host_employee.email:
        recipients.add(host_employee.email)
        log_recipients.append(f"Host:{host_employee.email}")

    # Добавляем директора
    if visit.department and visit.department.director and visit.department.director.email:
        recipients.add(visit.department.director.email)
        log_recipients.append(f"Director:{visit.department.director.email}")
    elif visit.department and visit.department.director:
        logger.warning(
            "Director '%s' for dept '%s' has no email.",
            visit.department.director.username,
            visit.department.name,
        )
    elif visit.department:
        logger.warning(
            "Department '%s' has no director assigned.",
            visit.department.name,
        )

    # Добавляем регистратора
    if visit.registered_by and visit.registered_by.email:
        recipients.add(visit.registered_by.email)
        log_recipients.append(f"Registrar:{visit.registered_by.email}")

    if not recipients:
        logger.warning(
            "No recipients found for visit %s ID %s. Notification not sent.",
            visit_kind,
            visit_id,
        )
        return False

    subject = f"Уведомление о планируемом визите: {visit.guest.full_name}"
    context = {'visit': visit, 'visit_kind': visit_kind}
    try:
        # Можно использовать только текстовый шаблон для простоты
        message_txt = render_to_string('notifications/visit_notification.txt', context)
        # message_html = render_to_string('notifications/email/visit_notification.html', context)
        logger.debug("Sending visit notification email to: %s", recipients)
        if EMAIL_SEND_TOTAL:
            EMAIL_SEND_TOTAL.labels(kind='visit_creation').inc()
        send_mail(
            subject, message_txt, settings.DEFAULT_FROM_EMAIL,
            list(recipients), fail_silently=False#, html_message=message_html
        )
        logger.info(
            "Visit notification email for %s ID %s SENT successfully to %s.",
            visit_kind,
            visit_id,
            log_recipients,
        )
        return True
    except (BadHeaderError, SMTPException, TemplateDoesNotExist) as exc:
        if EMAIL_SEND_FAILURES:
            EMAIL_SEND_FAILURES.labels(kind='visit_creation').inc()
        logger.exception(
            "Core email sending FAILED for visit %s ID %s to %s: %s.",
            visit_kind,
            visit_id,
            recipients,
            exc,
        )
        return False

def send_new_visit_notification_to_security(visit_or_group_instance, visit_kind):
    """
    Отправляет уведомление о новом зарегистрированном визите
    членам группы SECURITY_NOTIFICATION_GROUP_NAME.
    """
    try:
        security_group = Group.objects.get(name=SECURITY_NOTIFICATION_GROUP_NAME)
        recipients = User.objects.filter(groups=security_group, is_active=True).exclude(email__exact='')
    except Group.DoesNotExist:
        logger.error(
            "Группа '%s' не найдена. Уведомления безопасности не будут отправлены.",
            SECURITY_NOTIFICATION_GROUP_NAME,
        )
        return
    except DatabaseError as exc:
        logger.error(
            "Ошибка при получении пользователей из группы безопасности: %s",
            exc,
        )
        return

    if not recipients.exists():
        logger.info(
            "В группе '%s' нет активных пользователей с email для отправки уведомлений.",
            SECURITY_NOTIFICATION_GROUP_NAME,
        )
        return

    recipient_emails = [user.email for user in recipients if user.email]

    if not recipient_emails:
        logger.info(
            "Не найдено email адресов у пользователей группы '%s'.",
            SECURITY_NOTIFICATION_GROUP_NAME,
        )
        return

    subject_template_name = 'notifications/email/security_new_visit_notification_subject.txt'
    html_body_template_name = 'notifications/email/security_new_visit_notification_body.html'
    # text_body_template_name = 'notifications/email/security_new_visit_notification_body.txt' # Опционально

    context = {
        'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
    }
    
    if visit_kind == 'group':
        # Ожидаем объект GroupInvitation
        visit_group = visit_or_group_instance
        context.update({
            'visit_group': visit_group,
            'visit_kind_display': f"Групповой визит: {visit_group.group_name or 'Без названия'}",
            'guests_list': list(visit_group.guests.all()),
        })
        # Для темы письма используем имя группы или первого гостя
        first_guest_name = visit_group.guests.first().full_name if visit_group.guests.exists() else "Группа"
        subject_context_name = visit_group.group_name or (first_guest_name + " и др.")
    else: # official или student
        visit_instance = visit_or_group_instance
        context.update({
            'visit': visit_instance,
            'visit_kind_display': "Гость к сотруднику" if visit_kind == 'official' else "Студент/Абитуриент",
        })
        subject_context_name = visit_instance.guest.full_name

    # Обновляем контекст для темы письма
    subject_render_context = {'subject_guest_name': subject_context_name}
    try:
        subject = render_to_string(subject_template_name, subject_render_context).strip()
        html_message = render_to_string(html_body_template_name, context)
    except TemplateDoesNotExist as exc:
        logger.error("Шаблон уведомления не найден: %s", exc)
        return

    try:
        if EMAIL_SEND_TOTAL:
            EMAIL_SEND_TOTAL.labels(kind=f'new_visit_{visit_kind}').inc()
        send_mail(
            subject,
            '',  # Используем html_message, поэтому plain_message можно оставить пустым
            settings.DEFAULT_FROM_EMAIL,
            recipient_emails,
            html_message=html_message,
            fail_silently=False,
        )
        entity_id = getattr(visit_or_group_instance, 'id', 'n/a')
        logger.info(
            "Уведомление о новом визите (%s ID: %s) успешно отправлено группе безопасности.",
            visit_kind,
            entity_id,
        )
    except (BadHeaderError, SMTPException) as exc:
        if EMAIL_SEND_FAILURES:
            EMAIL_SEND_FAILURES.labels(kind=f'new_visit_{visit_kind}').inc()
        logger.error(
            "Ошибка при отправке уведомления о новом визите группе безопасности: %s",
            exc,
        )


# WebPush функции

def send_webpush_notification(user, title, body, data=None, badge=None, icon=None):
    """
    Отправка WebPush уведомления пользователю
    
    Args:
        user: Django User объект
        title: Заголовок уведомления
        body: Текст уведомления
        data: Дополнительные данные (dict)
        badge: Значок для уведомления
        icon: Иконка уведомления
    
    Returns:
        dict: {
            'success': bool,
            'sent_count': int,
            'errors': list
        }
    """
    if not send_user_notification:
        logger.warning("WebPush библиотека не установлена")
        return {'success': False, 'sent_count': 0, 'errors': ['WebPush не настроен']}
    
    # Импортируем наши модели
    from .models import WebPushSubscription, WebPushMessage
    
    # Получаем активные подписки пользователя
    subscriptions = WebPushSubscription.objects.filter(
        user=user,
        is_active=True
    )
    
    if not subscriptions.exists():
        logger.info(f'У пользователя {user.username} нет активных WebPush подписок')
        return {'success': True, 'sent_count': 0, 'errors': []}
    
    # Формируем payload
    payload = {
        'title': title,
        'body': body,
        'icon': icon or '/static/img/icons/icon-192x192.png',
        'badge': badge or '/static/img/icons/badge.png',
        'timestamp': int(timezone.now().timestamp() * 1000),
    }
    
    if data:
        payload['data'] = data
    
    sent_count = 0
    errors = []
    
    # Отправляем уведомления всем подпискам
    for subscription in subscriptions:
        try:
            if WEBPUSH_SEND_TOTAL:
                WEBPUSH_SEND_TOTAL.inc()
            
            # Используем django-webpush для отправки
            send_user_notification(
                user=user,
                payload=payload,
                ttl=1000
            )
            
            # Логируем успешную отправку
            WebPushMessage.objects.create(
                subscription=subscription,
                title=title,
                body=body,
                success=True
            )
            
            sent_count += 1
            logger.info(f'WebPush уведомление отправлено пользователю {user.username}')
            
        except Exception as e:
            if WEBPUSH_SEND_FAILURES:
                WEBPUSH_SEND_FAILURES.inc()
            
            error_msg = str(e)
            errors.append(error_msg)
            
            # Логируем ошибку
            WebPushMessage.objects.create(
                subscription=subscription,
                title=title,
                body=body,
                success=False,
                error_message=error_msg
            )
            
            logger.error(
                f'Ошибка отправки WebPush пользователю {user.username}: {error_msg}'
            )
            
            # Если подписка недействительна, деактивируем её
            if 'invalid' in error_msg.lower() or 'expired' in error_msg.lower():
                subscription.is_active = False
                subscription.save()
                logger.info(f'Подписка {subscription.id} деактивирована из-за ошибки')
    
    success = sent_count > 0
    return {
        'success': success,
        'sent_count': sent_count,
        'errors': errors
    }


def send_webpush_to_multiple_users(users, title, body, data=None):
    """
    Отправка WebPush уведомлений нескольким пользователям
    
    Args:
        users: QuerySet или список пользователей
        title: Заголовок уведомления
        body: Текст уведомления
        data: Дополнительные данные
    
    Returns:
        dict: Результат отправки
    """
    total_sent = 0
    total_errors = []
    
    for user in users:
        result = send_webpush_notification(user, title, body, data)
        total_sent += result['sent_count']
        total_errors.extend(result['errors'])
    
    return {
        'success': total_sent > 0,
        'sent_count': total_sent,
        'errors': total_errors
    }


def create_notification_with_webpush(recipient, title, message,
                                     notification_type='system',
                                     send_push=True, **kwargs):
    """
    Создает уведомление в БД и опционально отправляет WebPush
    
    Args:
        recipient: User объект
        title: Заголовок
        message: Сообщение
        notification_type: Тип уведомления
        send_push: Отправлять ли WebPush
        **kwargs: Дополнительные поля для Notification
    
    Returns:
        tuple: (notification_object, webpush_result)
    """
    from .models import Notification
    
    # Создаем уведомление в БД
    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        **kwargs
    )
    
    webpush_result = None
    if send_push:
        # Отправляем WebPush
        webpush_result = send_webpush_notification(
            user=recipient,
            title=title,
            body=message,
            data={
                'notification_id': notification.id,
                'type': notification_type,
                'url': kwargs.get('action_url', ''),
            }
        )
    
    return notification, webpush_result
