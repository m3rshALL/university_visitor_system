from django.apps import AppConfig


class RealtimeDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'realtime_dashboard'
    verbose_name = 'Дашборд в реальном времени'
    
    def ready(self):
        import realtime_dashboard.signals
