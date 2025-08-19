from django.apps import AppConfig


class EgovIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'egov_integration'
    verbose_name = 'Интеграция с egov.kz'