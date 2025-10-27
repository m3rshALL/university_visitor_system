from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Visit, StudentVisit, AuditLog


def _safe_write_audit(action: str, model: str, obj_id: str, actor, extra=None):
    try:
        AuditLog.objects.create(
            action=action,
            model=model,
            object_id=obj_id,
            actor=actor,
            extra=extra or {},
        )
    except Exception:
        # Не бросаем исключения из сигналов
        pass


@receiver(post_save, sender=Visit)
def audit_visit_create_update(instance: Visit, created: bool, **kwargs):
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    _safe_write_audit(action, 'Visit', str(instance.pk), getattr(instance, 'registered_by', None))


@receiver(post_save, sender=StudentVisit)
def audit_student_visit_create_update(instance: StudentVisit, created: bool, **kwargs):
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    _safe_write_audit(action, 'StudentVisit', str(instance.pk), getattr(instance, 'registered_by', None))

# visitors/signals.py

from django.conf import settings  # Для ссылки на модель User
from django.dispatch import receiver
from django.contrib.auth import get_user_model
# from notifications.tasks import send_visit_notification_task # Импортируем задачу для отправки уведомлений
# Импортируем ваши модели User (хотя settings.AUTH_USER_MODEL лучше) и EmployeeProfile
# from django.contrib.auth.models import User # Менее гибко
# from .models import EmployeeProfile # Убедитесь, что EmployeeProfile импортирован
# from .models import Visit, StudentVisit # Импортируем модели Visit и StudentVisit

# Используем реальную модель пользователя
UserModel = get_user_model()

# --- Обработчик для модели Visit ---
@receiver(post_save, sender='visitors.Visit')
def notify_on_visit_creation(instance, created, **kwargs):
    """Отправляет уведомление при создании нового Visit."""
    from notifications.tasks import send_visit_notification_task
    from django.db import transaction
    if created: # Отправляем только при СОЗДАНИИ записи
        import logging
        logging.getLogger(__name__).info(
            "Создан Visit ID: %s, запуск задачи уведомления...", instance.id
        )
        # Запускаем асинхронную задачу ПОСЛЕ коммита транзакции
        transaction.on_commit(
            lambda: send_visit_notification_task.delay(instance.id, 'official')
        )
# ----------------------------------



# --- Обработчик для модели StudentVisit ---
@receiver(post_save, sender='visitors.StudentVisit')
def notify_on_student_visit_creation(instance, created, **kwargs):
    """Отправляет уведомление при создании нового StudentVisit."""
    from notifications.tasks import send_visit_notification_task
    from django.db import transaction
    if created:  # Отправляем только при СОЗДАНИИ записи
        import logging
        logging.getLogger(__name__).info(
            "Создан StudentVisit ID: %s, запуск задачи уведомления...", instance.id
        )
        # Запускаем асинхронную задачу ПОСЛЕ коммита транзакции
        transaction.on_commit(
            lambda: send_visit_notification_task.delay(instance.id, 'student')
        )
# ---------------------------------------

# Этот приемник будет срабатывать КАЖДЫЙ раз после сохранения объекта User
@receiver(post_save, sender=UserModel)
def create_or_update_employee_profile(instance, created, **kwargs):
    """
    Создает EmployeeProfile для нового пользователя или просто убеждается,
    что он существует для существующего пользователя.
    """
    # --- ИМПОРТИРУЕМ МОДЕЛЬ ЗДЕСЬ ---
    from .models import EmployeeProfile
    # -------------------------------

    # Убеждаемся, что профиль существует
    EmployeeProfile.objects.get_or_create(user=instance)

    if created: # Если пользователь был только что СОЗДАН
        # Можно добавить логику, выполняемую только при создании профиля
        # Например, попытаться вытащить данные из allauth (но это сложнее)
        import logging
        logging.getLogger(__name__).info(
            "Создан профиль для нового пользователя %s", instance.username
        )
        pass
    else: # Если пользователь ОБНОВЛЕН (не создан)
        # Можно добавить логику обновления профиля, если нужно,
        # но обычно данные профиля (телефон, департамент) меняются реже
        # и могут управляться через админку или отдельную форму редактирования профиля.
        # Убедились, что профиль существует через get_or_create.
        pass

    # TODO (Продвинутый уровень): Попытка заполнить из данных allauth.
    # Это потребует подключения к сигналам allauth (напр. pre_social_login)
    # и парсинга sociallogin.account.extra_data, а также маппинга
    # названий департаментов из Azure AD на ваши объекты Department.

    # Пример (очень упрощенно, НЕ ГАРАНТИРУЕТ РАБОТУ без доп. настройки):
    # try:
    #     # Пытаемся получить данные из связанного соц. аккаунта (если он есть)
    #     social_account = instance.socialaccount_set.filter(provider='microsoft').first()
    #     if social_account:
    #         extra_data = social_account.extra_data
    #         # Имена полей 'telephoneNumber', 'department' могут отличаться!
    #         phone = extra_data.get('telephoneNumber')
    #         dept_name = extra_data.get('department')
    #
    #         if phone and not profile.phone_number: # Заполняем только если пусто
    #             profile.phone_number = phone
    #             profile.save()
    #             print(f"Обновлен телефон для {instance.username}")
    #
    #         if dept_name and not profile.department: # Заполняем только если пусто
    #             try:
    #                 department_obj = Department.objects.get(name__iexact=dept_name) # Ищем департамент по имени
    #                 profile.department = department_obj
    #                 profile.save()
    #                 print(f"Привязан департамент {dept_name} для {instance.username}")
    #             except Department.DoesNotExist:
    #                 print(f"Департамент '{dept_name}' не найден в базе данных для {instance.username}")
    # except AttributeError:
    #      # У пользователя может не быть socialaccount_set
    #      pass


# FIX #5: Автоматический отзыв доступа при изменении статуса визита
@receiver(post_save, sender=Visit)
def revoke_access_on_status_change(instance: Visit, created: bool, **kwargs):
    """
    Автоматически отзывает доступ в HikCentral при:
    - Отмене визита (status='CANCELLED')
    - Завершении визита (status='CHECKED_OUT')
    
    Запускает revoke_access_level_task только если:
    - Визит не новый (created=False)
    - Доступ был выдан (access_granted=True)
    - Доступ еще не отозван (access_revoked=False)
    - Статус изменен на CANCELLED или CHECKED_OUT
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Игнорируем новые визиты
    if created:
        return
    
    # Проверяем условия для отзыва доступа
    if instance.status in ['CANCELLED', 'CHECKED_OUT']:
        if instance.access_granted and not instance.access_revoked:
            try:
                from hikvision_integration.tasks import revoke_access_level_task
                revoke_access_level_task.apply_async(
                    args=[instance.id],
                    countdown=5  # Задержка 5 секунд
                )
                logger.info(
                    'HikCentral: Scheduled access revoke for visit %s (status=%s)',
                    instance.id, instance.status
                )
            except Exception as exc:
                logger.warning(
                    'Failed to schedule access revoke for visit %s: %s',
                    instance.id, exc
                )


# FIX #8: Обновление validity в HikCentral при изменении времени визита
# ОТКЛЮЧЕНО: Поле expected_exit_time не существует в модели Visit
# Функционал update_person_validity_task может вызываться вручную при необходимости
# @receiver(post_save, sender=Visit)
def update_hikcentral_validity_on_time_change(instance: Visit, created: bool, **kwargs):
    """
    ОТКЛЮЧЕНО: Обновление validity в HikCentral при изменении времени визита.
    
    Причина: Поле expected_exit_time не существует в модели Visit.
    Задача update_person_validity_task использует HIKCENTRAL_ACCESS_END_TIME из settings.
    """
    pass


# ==================== CACHE INVALIDATION SIGNALS ====================

from django.core.cache import cache
import logging

cache_logger = logging.getLogger(__name__)


@receiver(post_save, sender='visitors.SecurityIncident')
def invalidate_security_incidents_cache(sender, instance, **kwargs):
    """
    Очистка кэша Security Incidents Dashboard при создании/обновлении инцидента.
    """
    try:
        # Очищаем все варианты cache keys для security incidents dashboard
        cache_pattern = 'dashboard:incidents:*'
        
        # Т.к. Redis не поддерживает wildcard delete в django-redis напрямую,
        # очищаем основные варианты фильтров
        filters = [
            ('active', '', ''),
            ('all', '', ''),
            ('resolved', '', ''),
            ('false_alarm', '', ''),
        ]
        
        for status, severity, type_ in filters:
            cache_key = f'dashboard:incidents:{status}:{severity}:{type_}'
            cache.delete(cache_key)
        
        # Также очищаем auto_checkin dashboard т.к. там показываются incidents
        cache.delete_pattern('dashboard:auto_checkin:*')
        
        cache_logger.debug(f'Cache invalidated for SecurityIncident #{instance.id}')
    except Exception as e:
        cache_logger.error(f'Error invalidating security incidents cache: {e}')


@receiver(post_save, sender='visitors.Visit')
def invalidate_visit_cache(sender, instance, **kwargs):
    """
    Очистка кэша Auto Check-in Dashboard при создании/обновлении визита.
    """
    try:
        # Очищаем auto_checkin dashboard для всех периодов
        periods = ['today', 'week', 'month']
        for period in periods:
            cache.delete_pattern(f'dashboard:auto_checkin:{period}:*')
        
        # Также очищаем hikcentral dashboard
        cache.delete('dashboard:hikcentral:status')
        
        cache_logger.debug(f'Cache invalidated for Visit #{instance.id}')
    except Exception as e:
        cache_logger.error(f'Error invalidating visit cache: {e}')


@receiver(post_save, sender='visitors.AuditLog')
def invalidate_auditlog_cache(sender, instance, **kwargs):
    """
    Очистка кэша Auto Check-in Dashboard при добавлении audit log записи.
    """
    # Только для автоматических check-in/out действий
    if instance.user_agent == 'HikCentral FaceID System':
        try:
            cache.delete_pattern('dashboard:auto_checkin:*')
            cache_logger.debug(f'Cache invalidated for AuditLog #{instance.id}')
        except Exception as e:
            cache_logger.error(f'Error invalidating auditlog cache: {e}')