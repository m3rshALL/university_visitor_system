from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Notification(models.Model):
    """Модель уведомлений пользователей"""
    NOTIFICATION_TYPES = [
        ('visit_approved', 'Визит одобрен'),
        ('visit_denied', 'Визит отклонен'),
        ('visit_reminder', 'Напоминание о визите'),
        ('guest_arrived', 'Гость прибыл'),
        ('booking_confirmed', 'Бронирование подтверждено'),
        ('booking_cancelled', 'Бронирование отменено'),
        ('system', 'Системное уведомление'),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications'
    )
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Сообщение')
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='system',
        verbose_name='Тип уведомления'
    )
    read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Создано')
    
    # Дополнительные данные для уведомлений
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    action_url = models.URLField(blank=True, verbose_name='Ссылка действия')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return f'{self.recipient.username}: {self.title}'


class WebPushSubscription(models.Model):
    """Модель для хранения подписок на WebPush уведомления"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='webpush_subscriptions'
    )
    endpoint = models.URLField(max_length=500, verbose_name='Endpoint')
    p256dh_key = models.CharField(max_length=255, verbose_name='P256DH Key')
    auth_key = models.CharField(max_length=255, verbose_name='Auth Key')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Создано')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    # Дополнительная информация
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    device_name = models.CharField(
        max_length=100, blank=True, verbose_name='Название устройства'
    )

    class Meta:
        unique_together = ['user', 'endpoint']
        verbose_name = 'WebPush подписка'
        verbose_name_plural = 'WebPush подписки'

    def __str__(self):
        return f'{self.user.username} - {self.device_name or "Unknown Device"}'


class WebPushMessage(models.Model):
    """Модель для логирования отправленных WebPush сообщений"""
    subscription = models.ForeignKey(WebPushSubscription, on_delete=models.CASCADE)
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, null=True, blank=True
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'WebPush сообщение'
        verbose_name_plural = 'WebPush сообщения'

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f'{status} {self.subscription.user.username}: {self.title}'
