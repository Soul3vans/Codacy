from django.apps import AppConfig


class GuiaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.guia'

    def ready(self):
        import apps.guia.signals