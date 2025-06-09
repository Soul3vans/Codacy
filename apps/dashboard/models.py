from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
    
    def __str__(self):
        return self.nombre

class Post(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('publicado', 'Publicado'),
        ('archivado', 'Archivado'),
    ]
    
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    contenido = models.TextField()
    resumen = models.TextField(max_length=300, help_text="Breve descripción del post")
    imagen_destacada = models.ImageField(upload_to='posts/', blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_publicacion = models.DateTimeField(blank=True, null=True)
    vistas = models.PositiveIntegerField(default=0)
    destacado = models.BooleanField(default=False)
    permitir_comentarios = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-fecha_publicacion', '-fecha_creacion']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
    
    def __str__(self):
        return self.titulo
    
    def get_absolute_url(self):
        return reverse('post_detalle', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if self.estado == 'publicado' and not self.fecha_publicacion:
            self.fecha_publicacion = timezone.now()
        super().save(*args, **kwargs)

class Comentario(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey( User, on_delete=models.CASCADE, related_name='comentarios_dashboard')
    contenido = models.TextField(max_length=500)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['fecha_creacion']
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
    
    def __str__(self):
        return f'Comentario de {self.autor.username} en {self.post.titulo}'

class Archivo(models.Model):
    TIPO_CHOICES = [
        ('imagen', 'Imagen'),
        ('documento', 'Documento'),
        ('video', 'Video'),
        ('otro', 'Otro'),
    ]
    
    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='archivos/')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True)
    subido_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='archivos_dashboard')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    publico = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'Archivo'
        verbose_name_plural = 'Archivos'
    
    def __str__(self):
        return self.nombre

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