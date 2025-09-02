from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import Role
from visitors.models import Visit

@receiver(post_save, sender=User)
def assign_default_role_and_group(sender, instance, created, **kwargs):
    """
    При создании нового пользователя назначает ему группу 'Simple Staff'
    и создает профиль сотрудника.
    """
    if created:
        # Назначаем группу по умолчанию
        try:
            group = Group.objects.get(name='Simple Staff')
            instance.groups.add(group)
        except Group.DoesNotExist:
            # Можно добавить логирование, если группа не найдена
            pass
        
        # Создаем профиль сотрудника
        # EmployeeProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=Role)
def assign_permissions_to_group(sender, instance, created, **kwargs):
    """
    При создании или обновлении роли, назначает соответствующие права
    связанной с ней группе.
    """
    group = instance.group
    
    # Очищаем все текущие права группы, чтобы избежать дублирования
    group.permissions.clear()

    # Получаем ContentType для модели Visit
    visit_content_type = ContentType.objects.get_for_model(Visit)

    # Общие права для всех аутентифицированных пользователей (управляются через 'Simple Staff')
    base_permissions = Permission.objects.filter(
        content_type=visit_content_type,
        codename__in=['add_visit', 'view_visit', 'change_visit', 'delete_visit']
    )

    if instance.name == Role.SIMPLE_STAFF:
        group.permissions.add(*base_permissions)

    elif instance.name == Role.DEPARTMENT_HEAD:
        # Глава департамента имеет базовые права + права на статистику и экспорт
        dept_head_permissions = Permission.objects.filter(
            content_type=visit_content_type,
            codename__in=['can_view_visit_statistics', 'can_export_statistics']
        )
        group.permissions.add(*base_permissions)
        group.permissions.add(*dept_head_permissions)

    elif instance.name in [Role.RECEPTIONIST, Role.SECURITY_GUARD, Role.ADMIN]:
        # Эти роли получают все возможные права на модель Visit
        all_visit_permissions = Permission.objects.filter(content_type=visit_content_type)
        group.permissions.add(*all_visit_permissions)

    # Для админа можно дополнительно выдать права на все модели, если требуется
    if instance.name == Role.ADMIN:
        # Даем все права на все модели
        all_permissions = Permission.objects.all()
        group.permissions.add(*all_permissions)
