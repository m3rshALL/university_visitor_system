from django.apps import AppConfig
from .signals import * # Импортируем сигналы, если они есть


class VisitorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'visitors'
    verbose_name = "Управление Посетителями" # Можно добавить для админки
    
    # Добавляем метод ready
    def ready(self):
        # Импортируем сигналы здесь, чтобы они были зарегистрированы при старте Django
        try:
            import visitors.signals # ИЛИ profiles.signals, если профиль в другом приложении
        except ImportError:
            pass # Обработка, если signals.py еще не создан
