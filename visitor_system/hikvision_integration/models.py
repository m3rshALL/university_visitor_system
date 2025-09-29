from django.db import models
from django.conf import settings


class HikCentralServer(models.Model):
    """Сервер HikCentral Professional"""
    name = models.CharField(max_length=100, verbose_name="Название сервера")
    base_url = models.URLField(verbose_name="URL сервера")
    integration_key = models.CharField(max_length=100, verbose_name="Integration Partner Key")
    integration_secret = models.CharField(max_length=200, verbose_name="Integration Partner Secret")
    username = models.CharField(max_length=128, verbose_name="Пользователь")
    password = models.CharField(max_length=256, verbose_name="Пароль")
    access_token = models.TextField(blank=True, null=True, verbose_name="Access Token")
    token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Токен истекает")
    enabled = models.BooleanField(default=True, verbose_name="Включен")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.base_url})"

    class Meta:
        verbose_name = "Сервер HikCentral"
        verbose_name_plural = "Серверы HikCentral"


class HikDevice(models.Model):
    name = models.CharField(max_length=100)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=80)
    username = models.CharField(max_length=128)
    password = models.CharField(max_length=256)
    verify_ssl = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=True)
    doors_json = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.host}:{self.port})"


class HikFaceLibrary(models.Model):
    device = models.ForeignKey(HikDevice, on_delete=models.CASCADE, related_name='face_libraries')
    library_id = models.CharField(max_length=64)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('device', 'library_id')

    def __str__(self) -> str:
        return f"{self.name} [{self.library_id}]"


class HikPersonBinding(models.Model):
    guest_id = models.IntegerField()
    device = models.ForeignKey(HikDevice, on_delete=models.CASCADE)
    person_id = models.CharField(max_length=64)
    face_id = models.CharField(max_length=64, blank=True, default='')
    access_from = models.DateTimeField(null=True, blank=True)
    access_to = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')  # pending/active/revoked/failed
    last_error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class HikAccessTask(models.Model):
    KIND_CHOICES = (
        ('enroll_face', 'Enroll Face'),
        ('revoke_access', 'Revoke Access'),
        ('sync_status', 'Sync Status'),
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default='queued')  # queued/running/success/failed
    attempts = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, default='')
    visit_id = models.IntegerField(null=True, blank=True)
    guest_id = models.IntegerField(null=True, blank=True)
    device = models.ForeignKey(HikDevice, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class HikEventLog(models.Model):
    device = models.ForeignKey(HikDevice, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField()
    resolved_visit_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
