"""Archivo se de señal para que se active la autogeneración de GuiaAutocontrol"""
# pylint: disable=import-error
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Archivo
from apps.guia.models import GuiaAutocontrol
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Archivo)
def crear_guia_desde_archivo(sender, instance, created, **kwargs):
    """
    La Señal para crear GuiaAutocontrol automáticamente cuando se guarda un nuevo archivo es
    con es_formulario=True o cuando se actualiza un archivo existente con es_formulario=True.
    """
    if instance.es_formulario:
        update_fields = kwargs.get('update_fields')
        if created or (update_fields and 'es_formulario' in update_fields):
            if not GuiaAutocontrol.objects.filter(archivo=instance).exists():
                try:
                    guia = GuiaAutocontrol.objects.create(
                        archivo=instance,
                        titulo_guia=instance.nombre,
                        activa=True
                    )
                    guia.extraer_contenido_archivo()
                    logger.info(f"Guía '{guia.titulo_guia}' creada automáticamente para el archivo: {instance.nombre}")
                except Exception as e:
                    logger.error(f"Error al crear guía automáticamente para el archivo {instance.nombre}: {e}")
