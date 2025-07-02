from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Defines the name for the Core app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Core"
