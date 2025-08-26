"""Сигналы Celery для сбора метрик"""

import logging
from celery.signals import (
    task_prerun, task_postrun, task_failure, task_retry,
    worker_ready, worker_shutting_down
)

try:
    from prometheus_client import Counter, Histogram, Gauge  # type: ignore
    
    # Celery метрики
    CELERY_TASKS_TOTAL = Counter(
        'celery_tasks_total',
        'Total number of Celery tasks',
        ['task_name', 'status']
    )
    
    CELERY_TASK_DURATION_SECONDS = Histogram(
        'celery_task_duration_seconds',
        'Celery task duration in seconds',
        ['task_name']
    )
    
    CELERY_WORKERS_ACTIVE = Gauge(
        'celery_workers_active',
        'Number of active Celery workers'
    )
    
    CELERY_TASKS_RUNNING = Gauge(
        'celery_tasks_running',
        'Number of currently running Celery tasks',
        ['task_name']
    )
    
    PROMETHEUS_AVAILABLE = True
    
except ImportError:
    PROMETHEUS_AVAILABLE = False
    CELERY_TASKS_TOTAL = None
    CELERY_TASK_DURATION_SECONDS = None
    CELERY_WORKERS_ACTIVE = None
    CELERY_TASKS_RUNNING = None

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Обработчик начала выполнения задачи"""
    if PROMETHEUS_AVAILABLE:
        task_name = task.name if task else sender
        CELERY_TASKS_RUNNING.labels(task_name=task_name).inc()


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Обработчик завершения выполнения задачи"""
    if PROMETHEUS_AVAILABLE:
        task_name = task.name if task else sender
        CELERY_TASKS_RUNNING.labels(task_name=task_name).dec()
        
        # Записываем успешное выполнение
        if state == 'SUCCESS':
            CELERY_TASKS_TOTAL.labels(task_name=task_name, status='success').inc()
            
            # Записываем длительность если есть информация
            if hasattr(task, '_start_time'):
                import time
                duration = time.time() - task._start_time
                CELERY_TASK_DURATION_SECONDS.labels(task_name=task_name).observe(duration)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Обработчик ошибки выполнения задачи"""
    if PROMETHEUS_AVAILABLE:
        task_name = sender.name if sender else 'unknown'
        CELERY_TASKS_TOTAL.labels(task_name=task_name, status='failure').inc()
        CELERY_TASKS_RUNNING.labels(task_name=task_name).dec()
        
        logger.error("Celery task failed: %s - %s", task_name, str(exception))


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Обработчик повтора задачи"""
    if PROMETHEUS_AVAILABLE:
        task_name = sender.name if sender else 'unknown'
        CELERY_TASKS_TOTAL.labels(task_name=task_name, status='retry').inc()
        
        logger.warning("Celery task retry: %s - %s", task_name, str(reason))


@worker_ready.connect
def worker_ready_handler(sender=None, **kwds):
    """Обработчик готовности worker'а"""
    if PROMETHEUS_AVAILABLE:
        CELERY_WORKERS_ACTIVE.inc()
        logger.info("Celery worker ready")


@worker_shutting_down.connect
def worker_shutting_down_handler(sender=None, **kwds):
    """Обработчик остановки worker'а"""
    if PROMETHEUS_AVAILABLE:
        CELERY_WORKERS_ACTIVE.dec()
        logger.info("Celery worker shutting down")
