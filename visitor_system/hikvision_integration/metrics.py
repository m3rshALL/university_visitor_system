"""
FIX #13: Prometheus metrics для HikCentral integration.

Метрики для мониторинга операций контроля доступа:
- hikcentral_access_assignments_total: Счётчик назначений доступа (status=success/failed)
- hikcentral_access_revocations_total: Счётчик отзывов доступа (status=success/failed)
- hikcentral_door_events_total: Счётчик событий проходов (event_type=entry/exit)
- hikcentral_guests_inside: Gauge количества гостей в здании
- hikcentral_api_requests_total: Счётчик API запросов (endpoint, status)
"""

try:
    from prometheus_client import Counter, Gauge

    # Счётчик назначений access level
    hikcentral_access_assignments_total = Counter(
        'hikcentral_access_assignments_total',
        'Total number of access level assignments',
        ['status']  # success, failed
    )

    # Счётчик отзывов access level
    hikcentral_access_revocations_total = Counter(
        'hikcentral_access_revocations_total',
        'Total number of access level revocations',
        ['status']  # success, failed
    )

    # Счётчик событий проходов через турникеты
    hikcentral_door_events_total = Counter(
        'hikcentral_door_events_total',
        'Total number of door passage events',
        ['event_type']  # entry, exit
    )

    # Gauge для количества гостей в здании (вошли но не вышли)
    hikcentral_guests_inside = Gauge(
        'hikcentral_guests_inside',
        'Number of guests currently inside the building'
    )

    # Счётчик API запросов к HikCentral
    hikcentral_api_requests_total = Counter(
        'hikcentral_api_requests_total',
        'Total number of HikCentral API requests',
        ['endpoint', 'status']  # endpoint path, http status code
    )

    # Счётчик ошибок при обработке задач
    hikcentral_task_errors_total = Counter(
        'hikcentral_task_errors_total',
        'Total number of task processing errors',
        ['task_name']
    )

    METRICS_AVAILABLE = True

except ImportError:
    # Prometheus client не установлен - создаём заглушки
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("prometheus_client not available, metrics disabled")

    class DummyMetric:
        def labels(self, **kwargs):
            return self
        
        def inc(self, amount=1):
            pass
        
        def set(self, value):
            pass

    hikcentral_access_assignments_total = DummyMetric()
    hikcentral_access_revocations_total = DummyMetric()
    hikcentral_door_events_total = DummyMetric()
    hikcentral_guests_inside = DummyMetric()
    hikcentral_api_requests_total = DummyMetric()
    hikcentral_task_errors_total = DummyMetric()

    METRICS_AVAILABLE = False
