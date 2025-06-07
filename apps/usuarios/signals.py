# myapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User # O tu CustomUser model
from .models import Perfil

@receiver(post_save, sender=User)
def crear_o_actualizar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance, es_admin=instance.is_superuser)
    else:
        # Actualiza es_admin si el usuario se convierte en superusuario o deja de serlo
        if hasattr(instance, 'perfil'):
            if instance.perfil.es_admin != instance.is_superuser:
                instance.perfil.es_admin = instance.is_superuser
                instance.perfil.save()
        else: # En caso de que un perfil no exista por alguna razón
            Perfil.objects.create(user=instance, es_admin=instance.is_superuser)