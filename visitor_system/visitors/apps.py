from django.apps import AppConfig

class VisitorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'visitors'
    verbose_name = "Управление Посетителями" # Можно добавить для админки