from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
import logging

from .models import Visit, StudentVisit, AuditLog

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def auto_close_expired_visits():
    """Автоматически закрывает просроченные визиты"""
    now = timezone.now()
    # Закрываем визиты, которые не были закрыты более 12 часов назад
    cutoff_time = now - timedelta(hours=12)
    
    expired_visits_count = 0
    expired_student_visits_count = 0
    
    try:
        with transaction.atomic():
            # Официальные визиты
            expired_visits = Visit.objects.filter(
                status='CHECKED_IN',
                entry_time__lt=cutoff_time,
                exit_time__isnull=True
            )
            
            for visit in expired_visits:
                visit.status = 'CHECKED_OUT'
                visit.exit_time = now
                visit.save(update_fields=['status', 'exit_time'])
                
                # Создаем audit log
                try:
                    AuditLog.objects.create(
                        action=AuditLog.ACTION_UPDATE,
                        model='Visit',
                        object_id=str(visit.pk),
                        actor=None,  # System action
                        ip_address='127.0.0.1',
                        user_agent='Celery Auto-Close Task',
                        path='/tasks/auto-close',
                        method='SYSTEM',
                        changes={
                            'reason': 'Auto-closed expired visit',
                            'cutoff_time': cutoff_time.isoformat(),
                            'auto_exit_time': now.isoformat()
                        }
                    )
                except Exception:
                    logger.exception('Failed to write AuditLog for auto-closed visit %s', visit.pk)
                
                expired_visits_count += 1
            
            # Студенческие визиты
            expired_student_visits = StudentVisit.objects.filter(
                status='CHECKED_IN',
                entry_time__lt=cutoff_time,
                exit_time__isnull=True
            )
            
            for visit in expired_student_visits:
                visit.status = 'CHECKED_OUT'
                visit.exit_time = now
                visit.save(update_fields=['status', 'exit_time'])
                
                # Создаем audit log
                try:
                    AuditLog.objects.create(
                        action=AuditLog.ACTION_UPDATE,
                        model='StudentVisit',
                        object_id=str(visit.pk),
                        actor=None,  # System action
                        ip_address='127.0.0.1',
                        user_agent='Celery Auto-Close Task',
                        path='/tasks/auto-close',
                        method='SYSTEM',
                        changes={
                            'reason': 'Auto-closed expired student visit',
                            'cutoff_time': cutoff_time.isoformat(),
                            'auto_exit_time': now.isoformat()
                        }
                    )
                except Exception:
                    logger.exception('Failed to write AuditLog for auto-closed student visit %s', visit.pk)
                
                expired_student_visits_count += 1
        
        if expired_visits_count > 0 or expired_student_visits_count > 0:
            logger.info(
                "Auto-closed %d expired visits and %d expired student visits",
                expired_visits_count,
                expired_student_visits_count
            )
        
        return {
            'expired_visits': expired_visits_count,
            'expired_student_visits': expired_student_visits_count,
            'cutoff_time': cutoff_time.isoformat()
        }
        
    except Exception as e:
        logger.error("Error in auto_close_expired_visits: %s", e)
        raise


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def cleanup_old_audit_logs():
    """Очищает старые audit logs (старше 90 дней)"""
    cutoff_date = timezone.now() - timedelta(days=90)
    
    try:
        with transaction.atomic():
            deleted_count, _ = AuditLog.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
        
        logger.info("Cleaned up %d old audit logs", deleted_count)
        return {'deleted_count': deleted_count, 'cutoff_date': cutoff_date.isoformat()}
        
    except Exception as e:
        logger.error("Error in cleanup_old_audit_logs: %s", e)
        raise
