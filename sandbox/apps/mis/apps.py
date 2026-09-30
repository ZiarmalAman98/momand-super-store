from django.apps import AppConfig


class MisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mis"
    verbose_name = "Store MIS"

    def ready(self):
        from . import signals  # noqa: F401
