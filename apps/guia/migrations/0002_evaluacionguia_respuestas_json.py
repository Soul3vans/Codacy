# Generated by Django 4.2.23 on 2025-07-02 23:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("guia", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluacionguia",
            name="respuestas_json",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Tabla de respuestas agrupadas por componente y pregunta",
            ),
        ),
    ]
