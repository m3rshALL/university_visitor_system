# visitors/signals.py

from django.conf import settings # Для ссылки на модель User
from django.db.models.signals import post_save
from django.dispatch import receiver
# from notifications.tasks import send_visit_notification_task # Импортируем задачу для отправки уведомлений
# Импортируем ваши модели User (хотя settings.AUTH_USER_MODEL лучше) и EmployeeProfile
# from django.contrib.auth.models import User # Менее гибко
# from .models import EmployeeProfile # Убедитесь, что EmployeeProfile импортирован
# from .models import Visit, StudentVisit # Импортируем модели Visit и StudentVisit

# Лучше использовать settings.AUTH_USER_MODEL для гибкости
User = settings.AUTH_USER_MODEL

# --- Обработчик для модели Visit ---
@receiver(post_save, sender='visitors.Visit')
def notify_on_visit_creation(sender, instance, created, **kwargs):
    from notifications.tasks import send_visit_notification_task
    """Отправляет уведомление при создании нового Visit."""
    if created: # Отправляем только при СОЗДАНИИ записи
        print(f"Создан Visit ID: {instance.id}, запуск задачи уведомления...")
        # Запускаем асинхронную задачу
        send_visit_notification_task.delay(instance.id, 'official')
# ----------------------------------

# --- Обработчик для модели StudentVisit ---
@receiver(post_save, sender='visitors.StudentVisit')
def notify_on_student_visit_creation(sender, instance, created, **kwargs):
    from notifications.tasks import send_visit_notification_task
    """Отправляет уведомление при создании нового StudentVisit."""
    if created: # Отправляем только при СОЗДАНИИ записи
        print(f"Создан StudentVisit ID: {instance.id}, запуск задачи уведомления...")
        # Запускаем асинхронную задачу
        send_visit_notification_task.delay(instance.id, 'student')
# ---------------------------------------

# Этот приемник будет срабатывать КАЖДЫЙ раз после сохранения объекта User
@receiver(post_save, sender=User)
def create_or_update_employee_profile(sender, instance, created, **kwargs):
    """
    Создает EmployeeProfile для нового пользователя или просто убеждается,
    что он существует для существующего пользователя.
    """
    # --- ИМПОРТИРУЕМ МОДЕЛЬ ЗДЕСЬ ---
    from .models import EmployeeProfile
    # -------------------------------

    # Используем get_or_create: он либо найдет существующий профиль,
    # либо создаст новый, если его нет. Это безопасно вызывать много раз.
    profile, profile_created = EmployeeProfile.objects.get_or_create(user=instance)

    if created: # Если пользователь был только что СОЗДАН
        # Можно добавить логику, выполняемую только при создании профиля
        # Например, попытаться вытащить данные из allauth (но это сложнее)
        print(f"Создан профиль для нового пользователя {instance.username}")
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