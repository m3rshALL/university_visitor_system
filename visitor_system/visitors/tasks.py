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
                
                # FIX #4: Отзываем доступ в HikCentral при автоматическом закрытии
                if visit.access_granted and not visit.access_revoked:
                    try:
                        from hikvision_integration.tasks import revoke_access_level_task
                        revoke_access_level_task.apply_async(
                            args=[visit.id],
                            countdown=5  # Задержка 5 секунд после сохранения
                        )
                        logger.info(
                            'HikCentral: Scheduled access revoke for auto-closed visit %s',
                            visit.id
                        )
                    except Exception as revoke_exc:
                        logger.warning(
                            'Failed to schedule access revoke for visit %s: %s',
                            visit.id, revoke_exc
                        )
                
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


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def analyze_security_events():
    """Анализирует события безопасности и отправляет алерты при подозрительной активности"""
    now = timezone.now()
    last_hour = now - timedelta(hours=1)
    
    try:
        # Проверяем на аномальную активность
        failed_logins = AuditLog.objects.filter(
            action=AuditLog.ACTION_LOGIN_FAILED,
            created_at__gte=last_hour
        )
        
        # Группируем по IP
        from django.db.models import Count
        suspicious_ips = failed_logins.values('ip_address').annotate(
            attempt_count=Count('id')
        ).filter(attempt_count__gte=10)  # Более 10 неудачных попыток за час
        
        alerts = []
        for ip_data in suspicious_ips:
            ip = ip_data['ip_address']
            count = ip_data['attempt_count']
            
            # Создаем запись об аномалии
            AuditLog.objects.create(
                action='security_alert',
                model='SecurityEvent',
                object_id=None,
                actor=None,
                ip_address=ip,
                extra={
                    'alert_type': 'suspicious_login_attempts',
                    'attempt_count': count,
                    'time_window': '1_hour',
                    'threshold': 10
                }
            )
            
            alerts.append({
                'type': 'suspicious_login_attempts',
                'ip': ip,
                'count': count
            })
        
        # Проверяем на массовые операции от одного пользователя
        bulk_actions = AuditLog.objects.filter(
            action__in=[AuditLog.ACTION_CREATE, AuditLog.ACTION_UPDATE, AuditLog.ACTION_DELETE],
            created_at__gte=last_hour
        ).values('actor').annotate(
            action_count=Count('id')
        ).filter(action_count__gte=50)  # Более 50 действий за час
        
        for user_data in bulk_actions:
            if user_data['actor']:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(pk=user_data['actor'])
                    AuditLog.objects.create(
                        action='security_alert',
                        model='SecurityEvent',
                        object_id=None,
                        actor=user,
                        extra={
                            'alert_type': 'bulk_operations',
                            'action_count': user_data['action_count'],
                            'time_window': '1_hour',
                            'threshold': 50
                        }
                    )
                    alerts.append({
                        'type': 'bulk_operations',
                        'user': user.username,
                        'count': user_data['action_count']
                    })
                except User.DoesNotExist:
                    pass
        
        if alerts:
            logger.warning("Security alerts detected: %s", alerts)
            # Здесь можно добавить отправку уведомлений администраторам
        
        return {
            'analyzed_period': f"{last_hour.isoformat()} - {now.isoformat()}",
            'alerts_count': len(alerts),
            'alerts': alerts
        }
        
    except Exception as e:
        logger.error("Error in analyze_security_events: %s", e)
        raise


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def generate_audit_report():
    """Генерирует ежедневный отчет по аудиту"""
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    
    try:
        # Статистика по действиям
        actions_stats = {}
        for action, _ in AuditLog.ACTION_CHOICES:
            count = AuditLog.objects.filter(
                action=action,
                created_at__gte=yesterday,
                created_at__lt=now
            ).count()
            actions_stats[action] = count
        
        # Топ активных пользователей
        from django.db.models import Count
        top_users = AuditLog.objects.filter(
            created_at__gte=yesterday,
            created_at__lt=now,
            actor__isnull=False
        ).values('actor__username').annotate(
            action_count=Count('id')
        ).order_by('-action_count')[:10]
        
        # Топ IP адресов
        top_ips = AuditLog.objects.filter(
            created_at__gte=yesterday,
            created_at__lt=now,
            ip_address__isnull=False
        ).values('ip_address').annotate(
            action_count=Count('id')
        ).order_by('-action_count')[:10]
        
        report = {
            'report_date': yesterday.date().isoformat(),
            'total_events': sum(actions_stats.values()),
            'actions_breakdown': actions_stats,
            'top_users': list(top_users),
            'top_ips': list(top_ips),
        }
        
        # Сохраняем отчет как аудит событие
        AuditLog.objects.create(
            action='daily_report',
            model='AuditReport',
            object_id=yesterday.date().isoformat(),
            actor=None,
            extra=report
        )
        
        logger.info("Generated daily audit report for %s", yesterday.date())
        return report
        
    except Exception as e:
        logger.error("Error in generate_audit_report: %s", e)
        raise


@shared_task(bind=True, max_retries=3)
def backup_database_task(self, upload_to_s3=False):
    """
    Celery task для автоматического резервного копирования базы данных.
    
    Args:
        upload_to_s3: Загружать ли backup в S3 (требует настройки AWS)
    
    Returns:
        dict: Информация о созданном backup
    """
    import logging
    from django.core.management import call_command
    from io import StringIO
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info('Starting automated database backup task')
        
        # Создаём StringIO буфер для захвата вывода команды
        out = StringIO()
        
        # Вызываем management command
        args = []
        if upload_to_s3:
            args.append('--s3')
        
        call_command('backup_database', *args, stdout=out)
        
        output = out.getvalue()
        logger.info(f'Database backup completed: {output}')
        
        return {
            'status': 'success',
            'output': output,
            'upload_to_s3': upload_to_s3
        }
        
    except Exception as exc:
        logger.error(f'Database backup failed: {exc}', exc_info=True)
        
        # Retry с exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 300 * (2 ** self.request.retries)  # 5min, 10min, 20min
            logger.warning(
                f'Retrying backup task in {countdown}s '
                f'(attempt {self.request.retries + 1}/{self.max_retries})'
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error('Max retries reached for backup task')
            raise