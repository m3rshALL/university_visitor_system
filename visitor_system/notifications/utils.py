# notifications/utils.py
import logging
import json
from django.conf import settings
from django.template.loader import render_to_string # Для HTML писем (опционально)
from django.core.mail import send_mail
from django.contrib.auth.models import User, Group # Добавляем Group

logger = logging.getLogger(__name__)

# Имя группы, члены которой будут получать уведомления о регистрации визитов
SECURITY_NOTIFICATION_GROUP_NAME = "Security Notifications" # Убедитесь, что это имя совпадает с созданным в админке

# Импортируем нужные модели из приложения visitors
try:
    from visitors.models import Visit, StudentVisit, Guest, Department
    MODELS_IMPORTED = True
except ImportError:
    logging.getLogger(__name__).error("CRITICAL: Could not import models from visitors app in notifications.utils!")
    MODELS_IMPORTED = False
# -------------------------------------

logger = logging.getLogger(__name__)

def send_guest_arrival_email(visit):
    """Отправляет email уведомление принимающему сотруднику о прибытии гостя."""
    employee = visit.employee
    guest = visit.guest

    if not employee.email:
        logger.warning(f"Не удалось отправить уведомление: у сотрудника {employee.username} нет email.")
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
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

        logger.info(f"Уведомление о прибытии гостя {guest.full_name} отправлено сотруднику {employee.email}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки email уведомления сотруднику {employee.email}: {e}", exc_info=True)
        # В реальном проекте здесь лучше использовать асинхронные задачи (Celery)
        # чтобы ошибка отправки не влияла на основной процесс регистрации
        return False

def send_visit_creation_notification(visit_id, visit_kind):
    """Отправляет email уведомление о создании визита директору и хосту."""
    logger.info(f"Attempting to send creation notification for {visit_kind} ID {visit_id}")
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
            logger.info(f"Notification skipped for StudentVisit ID {visit_id} as per current logic.")
            return True # Считаем успешным, т.к. не должны были отправлять
        else:
            logger.error(f"Unknown visit_kind '{visit_kind}' for notification (ID: {visit_id})")
            return False
    except (Visit.DoesNotExist, StudentVisit.DoesNotExist):
        logger.error(f"Visit {visit_kind} with ID {visit_id} not found for sending notification.")
        return False
    except Exception as e:
        logger.exception(f"Error fetching visit object {visit_kind} ID {visit_id} for notification.")
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
         logger.warning(f"Director '{visit.department.director.username}' for dept '{visit.department.name}' has no email.")
    elif visit.department:
         logger.warning(f"Department '{visit.department.name}' has no director assigned.")

    # Добавляем регистратора
    if visit.registered_by and visit.registered_by.email:
         recipients.add(visit.registered_by.email)
         log_recipients.append(f"Registrar:{visit.registered_by.email}")

    if not recipients:
        logger.warning(f"No recipients found for visit {visit_kind} ID {visit_id}. Notification not sent.")
        return False

    subject = f"Уведомление о планируемом визите: {visit.guest.full_name}"
    context = {'visit': visit, 'visit_kind': visit_kind}
    try:
        # Можно использовать только текстовый шаблон для простоты
        message_txt = render_to_string('notifications/visit_notification.txt', context)
        # message_html = render_to_string('notifications/email/visit_notification.html', context)
        logger.debug(f"Sending visit notification email to: {recipients}")
        send_mail(
            subject, message_txt, settings.DEFAULT_FROM_EMAIL,
            list(recipients), fail_silently=False#, html_message=message_html
        )
        logger.info(f"Visit notification email for {visit_kind} ID {visit_id} SENT successfully to {log_recipients}.")
        return True
    except Exception as e:
        logger.exception(f"Core email sending FAILED for visit {visit_kind} ID {visit_id} to {recipients}.")
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
        logger.error(f"Группа '{SECURITY_NOTIFICATION_GROUP_NAME}' не найдена. Уведомления безопасности не будут отправлены.")
        return
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей из группы безопасности: {e}")
        return

    if not recipients.exists():
        logger.info(f"В группе '{SECURITY_NOTIFICATION_GROUP_NAME}' нет активных пользователей с email для отправки уведомлений.")
        return

    recipient_emails = [user.email for user in recipients if user.email]

    if not recipient_emails:
        logger.info(f"Не найдено email адресов у пользователей группы '{SECURITY_NOTIFICATION_GROUP_NAME}'.")
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
    subject = render_to_string(subject_template_name, subject_render_context).strip()
    html_message = render_to_string(html_body_template_name, context)

    try:
        send_mail(
            subject,
            '', # Используем html_message, поэтому plain_message можно оставить пустым или использовать text_body_template_name
            settings.DEFAULT_FROM_EMAIL,
            recipient_emails,
            html_message=html_message,
            fail_silently=False,
        )
        try:
            entity_id = visit_or_group_instance.id
        except Exception:
            entity_id = 'n/a'
        logger.info("Уведомление о новом визите (%s ID: %s) успешно отправлено группе безопасности.", visit_kind, entity_id)
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о новом визите группе безопасности: {e}")
