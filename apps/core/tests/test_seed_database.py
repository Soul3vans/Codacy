from io import StringIO

from django.apps import apps
from django.core.management import call_command

from apps.accounts.models import User
from apps.core.management.commands.seed_database import NUMBER_OF_INSTANCES_TO_CREATE
from apps.core.test import TestCase


class SeedDatabaseTest(TestCase):
    def call_command(self, *args, **kwargs):
        out = StringIO()
        call_command(
            "seed_database",
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def test_province_instances_number(self):
        self.call_command()
        exempt_apps = ("accounts", "dashboard")
        for app_config in apps.get_app_configs():
            if (
                app_config.name.startswith("apps.")
                and app_config.label not in exempt_apps
            ):
                for model_name, model in app_config.models.items():
                    self.assertEqual(
                        model.objects.count(), NUMBER_OF_INSTANCES_TO_CREATE, model_name
                    )
        self.assertEqual(User.objects.count(), 1, "user")
