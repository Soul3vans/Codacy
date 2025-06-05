from django.db import models
from django.contrib.auth.models import User

class Perfil(models.Model):
    ROLES = [
        ('usuario', 'Usuario'),
        ('moderador', 'Moderador'),
        ('administrador', 'Administrador'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    es_admin = models.BooleanField(default=False)
    es_moderador = models.BooleanField(default=False)
    puede_editar = models.BooleanField(default=False)
    rol = models.CharField(max_length=20, choices=ROLES, default='usuario')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'
    
    def __str__(self):
        return f'{self.user.username} - {self.get_rol_display()}'
    
    def es_admin(self):
        return self.rol == 'administrador'
    
    def es_moderador(self):
        return self.rol == 'moderador'
    
    def puede_editar(self):
        return self.rol in ['administrador', 'moderador']
    
