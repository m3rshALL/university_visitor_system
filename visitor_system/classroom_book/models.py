from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Classroom(models.Model):
    """Модель аудитории"""
    number = models.CharField(max_length=10, unique=True, verbose_name='Номер аудитории')
    floor = models.IntegerField(verbose_name='Этаж')
    building = models.CharField(max_length=50, verbose_name='Блок')
    capacity = models.IntegerField(null=True, blank=True, verbose_name='Вместимость')
    features = models.TextField(blank=True, verbose_name='Особенности')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Аудитория'
        verbose_name_plural = 'Аудитории'
        ordering = ['building', 'floor', 'number']
    def __str__(self):
        return f"{self.number} ({self.building})"
    def get_available_key(self):
        """Возвращает доступный ключ для этой аудитории"""
        return self.keys.filter(is_available=True).first()
    def is_available(self, start_time, end_time):
        """Проверяет, свободна ли аудитория в указанное время"""
        # Исключаем завершенные бронирования
        overlapping = self.bookings.filter(
            is_cancelled=False,
            is_returned=False,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()
        return not overlapping

class ClassroomKey(models.Model):
    """Модель ключа от аудитории"""
    key_number = models.CharField(max_length=20, unique=True, verbose_name='Номер ключа')
    classroom = models.ForeignKey(
        Classroom, 
        on_delete=models.CASCADE,
        related_name='keys',
        verbose_name='Аудитория'
    )
    is_available = models.BooleanField(default=True, verbose_name='Доступен')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Ключ'
        verbose_name_plural = 'Ключи'
    def __str__(self):
        return f"Ключ #{self.key_number} ({self.classroom.number})"

class KeyBooking(models.Model):
    """Модель бронирования ключа"""
    STATUS_CHOICES = (
        ('reserved', 'Забронирован'),
        ('issued', 'Выдан'),
        ('returned', 'Возвращен'),
        ('expired', 'Просрочен'),
        ('cancelled', 'Отменен'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Аудитория'
    )
    key = models.ForeignKey(
        ClassroomKey,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bookings',
        verbose_name='Ключ'
    )
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='key_bookings',
        verbose_name='Преподаватель'
    )
    start_time = models.DateTimeField(
        db_index=True,  # Индекс для сортировки и фильтрации
        verbose_name='Время начала'
    )
    end_time = models.DateTimeField(verbose_name='Время окончания')
    purpose = models.CharField(max_length=255, verbose_name='Цель')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='reserved',
        db_index=True,  # Индекс для быстрой фильтрации по статусу
        verbose_name='Статус'
    )
    is_returned = models.BooleanField(default=False, verbose_name='Возвращен')
    returned_at = models.DateTimeField(null=True, blank=True, 
                                     verbose_name='Время возврата')
    is_cancelled = models.BooleanField(default=False, verbose_name='Отменен')
    qr_code_token = models.CharField(max_length=100, unique=True, blank=True, 
                                   null=True, verbose_name='Токен QR-кода')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Бронирование ключа'
        verbose_name_plural = 'Бронирования ключей'
        ordering = ['-start_time']
        indexes = [
            # Индексы для частых фильтраций и сортировок
            models.Index(fields=['status'], name='keybooking_status_idx'),
            models.Index(fields=['start_time'], name='keybooking_start_time_idx'),
            models.Index(fields=['end_time'], name='keybooking_end_time_idx'),
            models.Index(fields=['classroom'], name='keybooking_classroom_idx'),
            models.Index(fields=['teacher'], name='keybooking_teacher_idx'),
            # Составные индексы для комбинированных запросов
            models.Index(fields=['status', 'start_time'],
                         name='keybooking_status_start_idx'),
            models.Index(fields=['classroom', 'start_time'],
                         name='keybooking_classroom_start_idx'),
            models.Index(fields=['teacher', 'start_time'],
                         name='keybooking_teacher_start_idx'),
            # Индекс для поиска активных бронирований
            models.Index(fields=['is_returned', 'is_cancelled'],
                         name='keybooking_active_idx'),
        ]

    def __str__(self):
        return f"{self.classroom} ({self.start_time.strftime('%d.%m.%Y %H:%M')})"

    def save(self, *args, **kwargs):
        # Генерируем уникальный токен для QR-кода при создании
        if not self.qr_code_token:
            self.qr_code_token = uuid.uuid4().hex
        # Обновляем статус при возврате
        if self.is_returned and not self.returned_at:
            self.returned_at = timezone.now()
            self.status = 'returned'
            # Делаем ключ доступным снова
            if self.key:
                self.key.is_available = True
                self.key.save()
        # Обновляем статус при отмене
        if self.is_cancelled and self.status != 'cancelled':
            self.status = 'cancelled'
            # Делаем ключ доступным снова
            if self.key and not self.key.is_available:
                self.key.is_available = True
                self.key.save()
        super().save(*args, **kwargs)