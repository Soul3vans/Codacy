
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

class Post(models.Model):
    """Modelo para los posts del blog"""
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    contenido = models.TextField()
    resumen = models.TextField(max_length=300, blank=True)
    imagen_destacada = models.ImageField(upload_to='posts/', blank=True, null=True)
    
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_publicacion = models.DateTimeField(blank=True, null=True)
    
    publicado = models.BooleanField(default=False)
    destacado = models.BooleanField(default=False)
    
    # Métricas
    vistas = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    
    # SEO
    meta_descripcion = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return self.titulo
    
    def save(self, *args, **kwargs):
        # Generar slug automáticamente si no existe
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.titulo)
            
            # Asegurar que el slug sea único
            contador = 1
            slug_original = self.slug
            while Post.objects.filter(slug=self.slug).exists():
                self.slug = f"{slug_original}-{contador}"
                contador += 1
        
        # Establecer fecha de publicación si se publica por primera vez
        if self.publicado and not self.fecha_publicacion:
            self.fecha_publicacion = timezone.now()
        
        # Generar resumen automáticamente si no existe
        if not self.resumen and self.contenido:
            self.resumen = self.contenido[:297] + "..." if len(self.contenido) > 300 else self.contenido
        
        super().save(*args, **kwargs)
    
    @property
    def tiempo_lectura(self):
        """Calcula el tiempo estimado de lectura"""
        palabras = len(self.contenido.split())
        minutos = palabras // 200  # 200 palabras por minuto promedio
        return max(1, minutos)

class Categoria(models.Model):
    """Modelo para categorías de posts"""
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # Color hexadecimal
    icono = models.CharField(max_length=50, blank=True)  # Clase de ícono de FontAwesome
    
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre

# Agregar categorías a los posts
Post.add_to_class('categorias', models.ManyToManyField(Categoria, blank=True))

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
    
    # Metadatos
    tamaño = models.PositiveIntegerField(default=0)  # En bytes
    extension = models.CharField(max_length=10, blank=True)
    
    # Configuraciones
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

class Comentario(models.Model):
    """Modelo para comentarios en posts"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(default=timezone.now)
    
    # Comentarios anidados
    padre = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='respuestas')
    
    aprobado = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f'Comentario de {self.autor.username} en {self.post.titulo}'
