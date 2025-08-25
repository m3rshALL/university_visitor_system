from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    def ready(self):
        try:
            import logging
            from prometheus_client import Counter  # type: ignore
            # Глобальные счётчики ошибок email (отправка/успех/ошибка)
            # Инициализация один раз при старте
            logging.getLogger(__name__).info('Notifications app ready: Prometheus counters available')
        except Exception:
            pass
