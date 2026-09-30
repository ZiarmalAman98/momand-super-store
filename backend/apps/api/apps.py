from django.apps import AppConfig


class StoreApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.apps.api"
    label = "store_api"
    verbose_name = "Store API"
