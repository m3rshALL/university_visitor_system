# realtime_dashboard/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Q, Avg
from datetime import timedelta, datetime
import json


class DashboardMetric(models.Model):
    """
    Модель для хранения метрик дашборда
    """
    METRIC_TYPES = [
        ('visitors_count', 'Количество посетителей'),
        ('active_visits', 'Активные визиты'),
        ('today_registrations', 'Регистрации за сегодня'),
        ('avg_visit_duration', 'Средняя длительность визита'),
        ('department_stats', 'Статистика по департаментам'),
        ('hourly_stats', 'Почасовая статистика'),
        ('security_alerts', 'Предупреждения безопасности'),
    ]

    metric_type = models.CharField(
        max_length=50,
        choices=METRIC_TYPES,
        verbose_name="Тип метрики"
    )

    value = models.JSONField(
        default=dict,
        verbose_name="Значение метрики",
        help_text="JSON данные с метрикой"
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name="Время записи"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активная метрика"
    )

    class Meta:
        verbose_name = "Метрика дашборда"
        verbose_name_plural = "Метрики дашборда"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_type', 'timestamp']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.timestamp.strftime('%H:%M:%S')}"


class RealtimeEvent(models.Model):
    """
    Модель для событий в реальном времени
    """
    EVENT_TYPES = [
        ('visit_created', 'Новый визит'),
        ('visit_checked_in', 'Посетитель вошел'),
        ('visit_checked_out', 'Посетитель вышел'),
        ('visit_cancelled', 'Визит отменен'),
        ('security_alert', 'Предупреждение безопасности'),
        ('system_alert', 'Системное уведомление'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('critical', 'Критический'),
    ]

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name="Тип события"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='normal',
        verbose_name="Приоритет"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Заголовок события"
    )

    message = models.TextField(
        verbose_name="Сообщение"
    )

    data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Дополнительные данные"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Связанный пользователь"
    )

    visit = models.ForeignKey(
        'visitors.Visit',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Связанный визит"
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name="Прочитано"
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Время создания"
    )

    class Meta:
        verbose_name = "Событие в реальном времени"
        verbose_name_plural = "События в реальном времени"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"

    def mark_as_read(self):
        """Отметить как прочитанное"""
        self.is_read = True
        self.save(update_fields=['is_read'])


class DashboardWidget(models.Model):
    """
    Модель для виджетов дашборда
    """
    WIDGET_TYPES = [
        ('counter', 'Счетчик'),
        ('chart_line', 'Линейный график'),
        ('chart_bar', 'Столбчатый график'),
        ('chart_pie', 'Круговая диаграмма'),
        ('table', 'Таблица'),
        ('map', 'Карта'),
        ('activity_feed', 'Лента активности'),
        ('alert_list', 'Список предупреждений'),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name="Название виджета"
    )

    widget_type = models.CharField(
        max_length=30,
        choices=WIDGET_TYPES,
        verbose_name="Тип виджета"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Заголовок"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )

    config = models.JSONField(
        default=dict,
        verbose_name="Конфигурация виджета",
        help_text="JSON настройки виджета"
    )

    position_x = models.IntegerField(
        default=0,
        verbose_name="Позиция X"
    )

    position_y = models.IntegerField(
        default=0,
        verbose_name="Позиция Y"
    )

    width = models.IntegerField(
        default=4,
        verbose_name="Ширина (в колонках)"
    )

    height = models.IntegerField(
        default=3,
        verbose_name="Высота (в строках)"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )

    refresh_interval = models.IntegerField(
        default=30,
        verbose_name="Интервал обновления (секунды)"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Создал"
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Создан"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлен"
    )

    class Meta:
        verbose_name = "Виджет дашборда"
        verbose_name_plural = "Виджеты дашборда"
        ordering = ['position_y', 'position_x']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['position_y', 'position_x']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_widget_type_display()})"


# Пресеты удалены по требованию
