# visitor_system/celery.py
import os

from celery import Celery  # type: ignore  # pylint: disable=import-error
from celery.schedules import crontab

# Устанавливаем модуль настроек из окружения (по умолчанию dev)
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    os.getenv('DJANGO_SETTINGS_MODULE', 'visitor_system.conf.dev'),
)

app = Celery('visitor_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Подключаем сигналы для метрик
try:
    from . import celery_signals  # noqa: F401
except ImportError:
    pass

# Настройка Celery Beat для периодических задач

app.conf.beat_schedule = {
    'auto-close-expired-visits': {
        'task': 'visitors.tasks.auto_close_expired_visits',
        'schedule': crontab(minute='*/15'),  # Каждые 15 минут
    },
    'update-dashboard-metrics': {
        'task': 'realtime_dashboard.tasks.update_dashboard_metrics',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут
    },
    'cleanup-old-audit-logs': {
        'task': 'visitors.tasks.cleanup_old_audit_logs',
        'schedule': crontab(hour=2, minute=0),  # Ежедневно в 2:00
    },
    'analyze-security-events': {
        'task': 'visitors.tasks.analyze_security_events',
        'schedule': crontab(minute=0),  # Каждый час
    },
    'generate-audit-report': {
        'task': 'visitors.tasks.generate_audit_report',
        'schedule': crontab(hour=6, minute=0),  # Ежедневно в 6:00
    },
    'send-daily-visit-summary': {
        'task': 'notifications.tasks.send_daily_visit_summary',
        'schedule': crontab(hour=18, minute=0),  # Ежедневно в 18:00
    },
    'monitor-guest-passages': {
        'task': 'hikvision_integration.tasks.monitor_guest_passages_task',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут (для авто check-in/out)
    },
    'backup-database': {
        'task': 'visitors.tasks.backup_database_task',
        'schedule': crontab(hour=3, minute=0),  # Ежедневно в 3:00
        'kwargs': {'upload_to_s3': False},  # Измените на True если настроен S3
    },
}

app.conf.timezone = 'Asia/Almaty'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    import logging
    logging.getLogger(__name__).debug('Request: %r', self.request)
