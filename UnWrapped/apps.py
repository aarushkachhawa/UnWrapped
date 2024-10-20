from django.apps import AppConfig


class UnWrappedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "UnWrapped"