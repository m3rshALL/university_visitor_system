from django.db import models
from django.contrib.auth.models import Group

class Role(models.Model):
    """
    Модель для определения ролей пользователей в системе.
    """
    SECURITY_GUARD = 'security'
    RECEPTIONIST = 'receptionist'
    DEPARTMENT_HEAD = 'dept_head'
    SIMPLE_STAFF = 'simple_staff'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (SECURITY_GUARD, 'Security Guard'),
        (RECEPTIONIST, 'Receptionist'),
        (DEPARTMENT_HEAD, 'Department Head'),
        (SIMPLE_STAFF, 'Simple Staff'),
        (ADMIN, 'Admin'),
    ]

    name = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        unique=True,
        db_index=True  # Индекс для быстрого поиска по роли
    )
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='role_info')

    def __str__(self):
        return self.get_name_display()

    @classmethod
    def get_role_by_name(cls, name):
        try:
            return cls.objects.get(name=name)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_admin_role(cls):
        return cls.get_role_by_name(cls.ADMIN)

    @classmethod
    def get_security_role(cls):
        return cls.get_role_by_name(cls.SECURITY_GUARD)

    @classmethod
    def get_reception_role(cls):
        return cls.get_role_by_name(cls.RECEPTIONIST)

    @classmethod
    def get_department_head_role(cls):
        return cls.get_role_by_name(cls.DEPARTMENT_HEAD)

    @classmethod
    def get_simple_staff_role(cls):
        return cls.get_role_by_name(cls.SIMPLE_STAFF)
