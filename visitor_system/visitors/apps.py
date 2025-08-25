from django.apps import AppConfig

class VisitorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'visitors'
    verbose_name = "Управление Посетителями" # Можно добавить для админки

    def ready(self):
        # Регистрация сигналов приложения
        try:
            import visitors.signals  # noqa: F401
        except Exception:
            # Не ломаем запуск, если в тестовой среде неполные зависимости
            pass