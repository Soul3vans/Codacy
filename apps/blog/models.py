from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from ckeditor_uploader.fields import RichTextUploadingField
from django.core.validators import FileExtensionValidator

class Category(models.Model):
    """Categorías para organizar los posts del blog"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    """Tags para etiquetar los posts"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Etiqueta"
        verbose_name_plural = "Etiquetas"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class BlogPost(models.Model):
    """Modelo principal para los posts del blog"""
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('published', 'Publicado'),
        ('archived', 'Archivado'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Título")
    slug = models.SlugField(max_length=200, unique=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Autor")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    # Contenido del post
    excerpt = models.TextField(max_length=300, verbose_name="Extracto", 
                              help_text="Breve descripción del post")
    content = RichTextUploadingField(verbose_name="Contenido")
    
    # Imagen destacada
    featured_image = models.ImageField(upload_to='blog/images/', blank=True, null=True,
                                     verbose_name="Imagen destacada")
    image_alt = models.CharField(max_length=200, blank=True, 
                               verbose_name="Texto alternativo de imagen")
    
    # SEO
    meta_description = models.CharField(max_length=160, blank=True,
                                      verbose_name="Meta descripción")
    meta_keywords = models.CharField(max_length=200, blank=True,
                                   verbose_name="Meta palabras clave")
    
    # Estado y fechas
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Campos adicionales
    is_featured = models.BooleanField(default=False, verbose_name="Post destacado")
    allow_comments = models.BooleanField(default=True, verbose_name="Permitir comentarios")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Contador de vistas")
    
    class Meta:
        verbose_name = "Post del Blog"
        verbose_name_plural = "Posts del Blog"
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

class Document(models.Model):
    """Modelo para documentos que pueden ser añadidos por moderadores"""
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'),
        ('doc', 'Documento Word'),
        ('xls', 'Hoja de cálculo'),
        ('ppt', 'Presentación'),
        ('img', 'Imagen'),
        ('video', 'Video'),
        ('other', 'Otro'),
    ]
    
    ACCESS_LEVELS = [
        ('public', 'Público'),
        ('private', 'Privado'),
        ('members', 'Solo miembros'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Título del documento")
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    # Archivo
    file = models.FileField(
        upload_to='documents/%Y/%m/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
                               'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov', 'txt']
        )],
        verbose_name="Archivo"
    )
    
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES, 
                                   default='other', verbose_name="Tipo de documento")
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name="Tamaño del archivo")
    
    # Metadatos
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, 
                                  verbose_name="Subido por")
    access_level = models.CharField(max_length=10, choices=ACCESS_LEVELS, 
                                  default='public', verbose_name="Nivel de acceso")
    
    # Relación con posts del blog
    related_posts = models.ManyToManyField(BlogPost, blank=True, 
                                         verbose_name="Posts relacionados")
    
    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Campos adicionales
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    download_count = models.PositiveIntegerField(default=0, 
                                               verbose_name="Contador de descargas")
    
    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_type', 'access_level']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            # Determinar tipo de documento basado en extensión
            extension = self.file.name.split('.')[-1].lower()
            if extension in ['pdf']:
                self.document_type = 'pdf'
            elif extension in ['doc', 'docx']:
                self.document_type = 'doc'
            elif extension in ['xls', 'xlsx']:
                self.document_type = 'xls'
            elif extension in ['ppt', 'pptx']:
                self.document_type = 'ppt'
            elif extension in ['jpg', 'jpeg', 'png', 'gif']:
                self.document_type = 'img'
            elif extension in ['mp4', 'avi', 'mov']:
                self.document_type = 'video'
        super().save(*args, **kwargs)
    
    def get_file_extension(self):
        return self.file.name.split('.')[-1].lower() if self.file else ''
    
    def get_file_size_display(self):
        if self.file_size:
            if self.file_size < 1024:
                return f"{self.file_size} B"
            elif self.file_size < 1024 * 1024:
                return f"{self.file_size / 1024:.1f} KB"
            else:
                return f"{self.file_size / (1024 * 1024):.1f} MB"
        return "N/A"

class BlogTemplate(models.Model):
    """Modelo para templates personalizables del blog"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre del template")
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    # Configuración del template
    header_content = RichTextUploadingField(blank=True, verbose_name="Contenido del header")
    footer_content = RichTextUploadingField(blank=True, verbose_name="Contenido del footer")
    sidebar_content = RichTextUploadingField(blank=True, verbose_name="Contenido del sidebar")
    
    # Configuración de colores y estilos
    primary_color = models.CharField(max_length=7, default='#007bff', 
                                   verbose_name="Color primario")
    secondary_color = models.CharField(max_length=7, default='#6c757d', 
                                     verbose_name="Color secundario")
    background_color = models.CharField(max_length=7, default='#ffffff', 
                                      verbose_name="Color de fondo")
    text_color = models.CharField(max_length=7, default='#212529', 
                                verbose_name="Color del texto")
    
    # Configuración de layout
    posts_per_page = models.PositiveIntegerField(default=10, 
                                               verbose_name="Posts por página")
    show_sidebar = models.BooleanField(default=True, verbose_name="Mostrar sidebar")
    show_categories = models.BooleanField(default=True, verbose_name="Mostrar categorías")
    show_tags = models.BooleanField(default=True, verbose_name="Mostrar tags")
    
    # CSS personalizado
    custom_css = models.TextField(blank=True, verbose_name="CSS personalizado")
    
    # Estado
    is_active = models.BooleanField(default=False, verbose_name="Template activo")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, 
                                 verbose_name="Creado por")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Template del Blog"
        verbose_name_plural = "Templates del Blog"
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_active:
            # Desactivar otros templates cuando se active uno nuevo
            BlogTemplate.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

class Comment(models.Model):
    """Modelo para comentarios en los posts"""
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, 
                           related_name='comments')
    author_name = models.CharField(max_length=100, verbose_name="Nombre")
    author_email = models.EmailField(verbose_name="Email")
    content = models.TextField(verbose_name="Comentario")
    
    is_approved = models.BooleanField(default=False, verbose_name="Aprobado")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Comentario"
        verbose_name_plural = "Comentarios"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comentario de {self.author_name} en {self.post.title}"
