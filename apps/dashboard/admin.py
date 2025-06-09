from django.contrib import admin
from .models import EnlaceInteres

@admin.register(EnlaceInteres)
class EnlaceInteresAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'categoria', 'activo', 'es_destacado', 'fecha_creacion')
    list_filter = ('categoria', 'activo', 'es_destacado')
    search_fields = ('titulo', 'descripcion')
    ordering = ('-es_destacado', 'orden', '-fecha_creacion')

