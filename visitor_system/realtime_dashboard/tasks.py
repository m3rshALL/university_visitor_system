from celery import shared_task
from django.core.cache import cache
import logging

from .services import DashboardMetricsService

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def update_dashboard_metrics():
    """Обновляет метрики дашборда и очищает кэш"""
    try:
        service = DashboardMetricsService()
        
        # Очищаем кэш метрик
        cache_keys_to_delete = [
            'dash:department_stats',
            'dash:events:limit=10',
            'dash:security_alerts',
        ]
        
        # Очищаем кэш по часам для hourly stats
        from django.utils import timezone
        current_hour = timezone.now().hour
        for hour in range(24):
            cache_keys_to_delete.append(f'dash:hourly_stats:{hour}')
        
        cache.delete_many(cache_keys_to_delete)
        
        # Прогреваем кэш основных метрик
        service.get_current_metrics()
        service.get_department_stats()
        service.get_hourly_stats()
        
        logger.info("Dashboard metrics updated and cache refreshed")
        return {'status': 'success', 'cleared_keys': len(cache_keys_to_delete)}
        
    except Exception as e:
        logger.error("Error updating dashboard metrics: %s", e)
        raise


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def cleanup_old_events():
    """Очищает старые события дашборда (старше 7 дней)"""
    from django.utils import timezone
    from datetime import timedelta
    from .models import RealtimeEvent
    
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        deleted_count, _ = RealtimeEvent.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        logger.info("Cleaned up %d old dashboard events", deleted_count)
        return {'deleted_count': deleted_count, 'cutoff_date': cutoff_date.isoformat()}
        
    except Exception as e:
        logger.error("Error cleaning up old events: %s", e)
        raise
