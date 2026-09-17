from django.apps import AppConfig


class AppQuimicoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_quimico'

    def ready(self):
        # Connect signal handlers (weight cache invalidation, etc.).
        from app_quimico import signals  # noqa: F401
