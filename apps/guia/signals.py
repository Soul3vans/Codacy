from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RespuestaGuia, EvaluacionGuia

@receiver(post_save, sender=RespuestaGuia)
def actualizar_evaluacion(sender, instance, created, **kwargs):
    """
    Señal que se activa después de guardar una respuesta.
    Actualiza la evaluación correspondiente.
    """
    evaluacion = EvaluacionGuia.objects.get(guia=instance.guia, usuario=instance.usuario)
    evaluacion.calcular_porcentaje_cumplimiento()
    evaluacion.save()
