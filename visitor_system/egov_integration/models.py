# egov_integration/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class DocumentVerification(models.Model):
    """
    Модель для хранения результатов проверки документов через egov.kz
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает проверки'),
        ('verified', 'Проверен'),
        ('failed', 'Ошибка проверки'),
        ('invalid', 'Недействительный документ'),
        ('expired', 'Просрочен'),
    ]
    
    DOCUMENT_TYPES = [
        ('iin', 'ИИН'),
        ('passport', 'Паспорт'),
        ('driving_license', 'Водительские права'),
        ('birth_certificate', 'Свидетельство о рождении'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Связь с гостем (если есть)
    guest = models.ForeignKey(
        'visitors.Guest', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='document_verifications',
        verbose_name="Гость"
    )
    
    # Данные документа (зашифровано)
    document_type = models.CharField(
        max_length=20, 
        choices=DOCUMENT_TYPES, 
        verbose_name="Тип документа"
    )
    document_number = models.CharField(
        max_length=255, 
        verbose_name="Номер документа (зашифровано)"
    )
    
    # Результаты проверки
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Статус проверки"
    )
    
    # Данные от egov.kz
    egov_response = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name="Ответ от egov.kz"
    )
    verified_data = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name="Проверенные данные"
    )
    
    # Метаданные
    requested_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Запросил проверку"
    )
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="Время запроса"
    )
    verified_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Время проверки"
    )
    
    # Дополнительные поля
    error_message = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Сообщение об ошибке"
    )
    retry_count = models.IntegerField(
        default=0, 
        verbose_name="Количество повторов"
    )
    
    class Meta:
        verbose_name = "Проверка документа"
        verbose_name_plural = "Проверки документов"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['document_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.get_status_display()}"
    
    def is_verified(self):
        return self.status == 'verified'
    
    def is_valid(self):
        return self.status in ['verified']


class EgovAPILog(models.Model):
    """
    Логи обращений к API egov.kz для мониторинга и отладки
    """
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Данные запроса
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    endpoint = models.CharField(max_length=500, verbose_name="Конечная точка")
    request_data = models.JSONField(null=True, blank=True, verbose_name="Данные запроса")
    
    # Данные ответа
    response_status = models.IntegerField(verbose_name="HTTP статус ответа")
    response_data = models.JSONField(null=True, blank=True, verbose_name="Данные ответа")
    
    # Метаданные
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Пользователь"
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        verbose_name="IP адрес"
    )
    user_agent = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="User Agent"
    )
    
    # Время выполнения
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="Время запроса"
    )
    response_time_ms = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="Время ответа (мс)"
    )
    
    # Связь с проверкой документа
    verification = models.ForeignKey(
        DocumentVerification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_logs',
        verbose_name="Связанная проверка"
    )
    
    class Meta:
        verbose_name = "Лог API egov.kz"
        verbose_name_plural = "Логи API egov.kz"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['response_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['endpoint']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.response_status}"
    
    def is_success(self):
        return 200 <= self.response_status < 300


class EgovSettings(models.Model):
    """
    Настройки интеграции с egov.kz
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Название настройки")
    value = models.TextField(verbose_name="Значение")
    description = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Описание"
    )
    is_encrypted = models.BooleanField(
        default=False, 
        verbose_name="Зашифровано"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Обновлено"
    )
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Обновил"
    )
    
    class Meta:
        verbose_name = "Настройка egov.kz"
        verbose_name_plural = "Настройки egov.kz"
        ordering = ['name']
    
    def __str__(self):
        return self.name