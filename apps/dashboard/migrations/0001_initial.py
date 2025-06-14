# Generated by Django 5.2.1 on 2025-06-08 18:19

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('descripcion', models.TextField(blank=True)),
                ('activa', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Categoría',
                'verbose_name_plural': 'Categorías',
            },
        ),
        migrations.CreateModel(
            name='Archivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200)),
                ('archivo', models.FileField(upload_to='archivos/')),
                ('tipo', models.CharField(choices=[('imagen', 'Imagen'), ('documento', 'Documento'), ('video', 'Video'), ('otro', 'Otro')], max_length=20)),
                ('descripcion', models.TextField(blank=True)),
                ('fecha_subida', models.DateTimeField(auto_now_add=True)),
                ('publico', models.BooleanField(default=False)),
                ('subido_por', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='archivos_dashboard', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Archivo',
                'verbose_name_plural': 'Archivos',
                'ordering': ['-fecha_subida'],
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('contenido', models.TextField()),
                ('resumen', models.TextField(help_text='Breve descripción del post', max_length=300)),
                ('imagen_destacada', models.ImageField(blank=True, null=True, upload_to='posts/')),
                ('estado', models.CharField(choices=[('borrador', 'Borrador'), ('publicado', 'Publicado'), ('archivado', 'Archivado')], default='borrador', max_length=20)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('fecha_publicacion', models.DateTimeField(blank=True, null=True)),
                ('vistas', models.PositiveIntegerField(default=0)),
                ('destacado', models.BooleanField(default=False)),
                ('permitir_comentarios', models.BooleanField(default=True)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to=settings.AUTH_USER_MODEL)),
                ('categoria', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dashboard.categoria')),
            ],
            options={
                'verbose_name': 'Post',
                'verbose_name_plural': 'Posts',
                'ordering': ['-fecha_publicacion', '-fecha_creacion'],
            },
        ),
        migrations.CreateModel(
            name='Comentario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contenido', models.TextField(max_length=500)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('activo', models.BooleanField(default=True)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comentarios_dashboard', to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comentarios', to='dashboard.post')),
            ],
            options={
                'verbose_name': 'Comentario',
                'verbose_name_plural': 'Comentarios',
                'ordering': ['fecha_creacion'],
            },
        ),
    ]
