"""
Modelos para la aplicación dashboard.
Este módulo contiene los modelos de datos para el sistema de dashboard,
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Archivo(models.Model):
    TIPO_CHOICES = [
        ('imagen', 'Imagen'),
        ('documento', 'Documento'),
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('otro', 'Otro'),
    ]
    
    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='archivos/')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True)
    subido_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='archivos_dashboard')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    publico = models.BooleanField(default=False)
    es_formulario = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'Archivo'
        verbose_name_plural = 'Archivos'
    
    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        # Si el archivo ya existe y se está actualizando, eliminar el archivo anterior
        if self.pk:
            try:
                old = Archivo.objects.get(pk=self.pk)
                if old.archivo and self.archivo != old.archivo:
                    old.archivo.delete(save=False)
            except Archivo.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        
    def get_nombre_archivo(self):
    # Obtener el nombre completo del archivo incluyendo la extensión, pero sin la ruta
        if self.archivo:
            return self.archivo.name.split('/')[-1]
        return ''

class EnlaceInteres(models.Model):
    CATEGORIAS_CHOICES = [
        ('', 'Sin categoría'),
        ('educativo', 'Educativo'),
        ('institucional', 'Institucional'),
        ('recursos', 'Recursos'),
        ('herramientas', 'Herramientas'),
        ('noticias', 'Noticias'),
        ('otros', 'Otros'),
    ]
    
    titulo = models.CharField(max_length=200, verbose_name='Título')
    url = models.URLField(verbose_name='URL')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    categoria = models.CharField(
        max_length=20, 
        choices=CATEGORIAS_CHOICES, 
        blank=True,
        verbose_name='Categoría'
    )
    imagen = models.ImageField(
        upload_to='enlaces/',
        blank=True,
        null=True,
        verbose_name='Imagen'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    es_destacado = models.BooleanField(default=False, verbose_name='Destacado')
    orden = models.IntegerField(default=0, verbose_name='Orden')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Fecha de modificación')
    creado_por = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Creado por'
    )
    
    class Meta:
        verbose_name = 'Enlace de Interés'
        verbose_name_plural = 'Enlaces de Interés'
        ordering = ['-es_destacado', 'orden', '-fecha_creacion']
    
    def __str__(self):
        return self.titulo
    
    def get_categoria_display_custom(self):
        """Retorna el nombre de la categoría capitalizado"""
        if self.categoria:
            return dict(self.CATEGORIAS_CHOICES)[self.categoria].capitalize()
        return 'Sin categoría'