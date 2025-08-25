from django.db import models
from django.conf import settings


class Department(models.Model):
    name = models.CharField(max_length=200, unique=True,
                           verbose_name="Название департамента")
    description = models.TextField(blank=True, null=True,
                                  verbose_name="Описание")
    director = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # Или PROTECT
        null=True,
        blank=True,  # Позволяем департаменту быть без директора
        related_name='directed_departments',
        verbose_name="Директор департамента"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Департамент"
        verbose_name_plural = "Департаменты"
