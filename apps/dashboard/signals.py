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
    if instance.es_formulario: # Check if es_formulario is True
        # Get the list of updated fields, if available
        update_fields = kwargs.get('update_fields')
        # Condition 1: It's a new Archivo and es_formulario is True
        # Condition 2: It's an existing Archivo and es_formulario was updated to True
        # For Condition 2, we need to ensure 'es_formulario' is in update_fields
        # We also need to consider cases where es_formulario was already True and other fields were updated.

        # If it's a new file, or if the 'es_formulario' field specifically changed
        if created or (update_fields and 'es_formulario' in update_fields):
            # Check if a GuiaAutocontrol already exists for this Archivo
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
