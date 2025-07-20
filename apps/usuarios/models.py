"""Modelo para el perfil del usuario"""
from django.db import models
from django.db.models import IntegerChoices, IntegerField
from django.contrib.auth.models import User
from django.urls import reverse 
from django.utils import timezone
import os
class CedeChoice(IntegerChoices):
    """Define las Cedes Universitarias"""
    uho_olm = 1, "Oscar Lucero Moya"
    uho_csm = 2, "Celia Sánchez Manduley"
    uho_jlc = 3, "José de la Luz y Caballero"
class Perfil(models.Model):
    """Modelo para el perfil del usuario"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=20, blank=True, help_text='Número de teléfono del usuario')
    cede = IntegerField(verbose_name="Cedes", choices=CedeChoice.choices, blank=True, null=True)
    cargo = models.CharField(max_length=50, blank=False, help_text='Cargo que ocupa')
    recibir_notificaciones = models.BooleanField(default=True, help_text='Si el usuario desea recibir notificaciones por email')
    es_moderador = models.BooleanField(default=False, help_text='Si el usuario tiene permisos de moderador')
    es_admin = models.BooleanField(default=False, help_text='Si el usuario tiene permisos de administrador')
    puede_editar = models.BooleanField(default=False, help_text='Si el usuario puede editar contenido')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    firma_digital = models.FileField(upload_to='firmas/', blank=True, null=True)
    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'Perfil de {self.user.get_full_name() or self.user.username}'

    def get_absolute_url(self):
        return reverse('perfil', kwargs={'pk': self.pk})

    @property
    def nombre_completo(self):
        """Retorna el nombre completo del usuario"""
        if self.user.first_name and self.user.last_name:
            return f'{self.user.first_name} {self.user.last_name}'
        return self.user.username

    def actualizar_actividad(self):
        """Actualiza la última actividad del usuario"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

    def es_online(self):
        """Verifica si el usuario está online basado en la última actividad"""
        if self.last_activity:
            from datetime import timedelta
            return self.last_activity > timezone.now() - timedelta(minutes=5)
        return False

    def save(self, *args, **kwargs):
        # Si es admin, automáticamente es moderador y puede editar
        if self.es_admin:
            self.es_moderador = True
            self.puede_editar = True
        # Si es moderador, puede editar
        elif self.es_moderador:
            self.puede_editar = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Elimina el archivo de avatar al eliminar el perfil"""
        if self.avatar and os.path.exists(self.avatar.path):
            os.remove(self.avatar.path)
        super().delete(*args, **kwargs)
class Archivo(models.Model):
    """Modelo para gestión de archivos"""
    TIPOS_ARCHIVO = [
        ('imagen', 'Imagen'),
        ('documento', 'Documento'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('otro', 'Otro'),
    ]
    nombre = models.CharField(max_length=255)
    archivo = models.FileField(upload_to='uploads/')
    tipo = models.CharField(max_length=20, choices=TIPOS_ARCHIVO, default='otro')
    descripcion = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_subida = models.DateTimeField(default=timezone.now)
    # Metadatos en bytes
    tamaño = models.PositiveIntegerField(default=0)
    extension = models.CharField(max_length=10, blank=True)
    publico = models.BooleanField(default=False)
    class Meta:
        verbose_name = 'Archivo'
        verbose_name_plural = 'Archivos'
        ordering = ['-fecha_subida']
    
    def __str__(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        if self.archivo:
            # Obtener información del archivo
            self.tamaño = self.archivo.size
            self.extension = os.path.splitext(self.archivo.name)[1].lower()
            # Determinar tipo automáticamente
            if self.extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.tipo = 'imagen'
            elif self.extension in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
                self.tipo = 'documento'
            elif self.extension in ['.mp4', '.avi', '.mkv', '.mov']:
                self.tipo = 'video'
            elif self.extension in ['.mp3', '.wav', '.flac', '.ogg']:
                self.tipo = 'audio'
            # Generar nombre si no existe
            if not self.nombre:
                self.nombre = os.path.splitext(os.path.basename(self.archivo.name))[0]
        super().save(*args, **kwargs)
    
    @property
    def es_imagen(self):
        return self.tipo == 'imagen'
    
    @property
    def tamaño_legible(self):
        """Convierte el tamaño en bytes a formato legible"""
        if self.tamaño < 1024:
            return f"{self.tamaño} B"
        elif self.tamaño < 1024 * 1024:
            return f"{self.tamaño / 1024:.1f} KB"
        elif self.tamaño < 1024 * 1024 * 1024:
            return f"{self.tamaño / (1024 * 1024):.1f} MB"
        else:
            return f"{self.tamaño / (1024 * 1024 * 1024):.1f} GB"
