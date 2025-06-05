from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import BlogPost, Document, BlogTemplate, Category, Tag, Comment

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'post_count', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    
    def post_count(self, obj):
        return obj.blogpost_set.count()
    post_count.short_description = 'Posts'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'post_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    
    def post_count(self, obj):
        return obj.blogpost_set.count()
    post_count.short_description = 'Posts'

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'status', 'is_featured', 
                   'views_count', 'published_at', 'created_at']
    list_filter = ['status', 'category', 'is_featured', 'allow_comments', 
                  'created_at', 'published_at']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    
    fieldsets = (
        ('Información básica', {
            'fields': ('title', 'slug', 'author', 'category', 'tags')
        }),
        ('Contenido', {
            'fields': ('excerpt', 'content')
        }),
        ('Imagen destacada', {
            'fields': ('featured_image', 'image_alt'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Configuración', {
            'fields': ('status', 'is_featured', 'allow_comments')
        }),
        ('Fechas', {
            'fields': ('published_at',),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['tags']
    
    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'category')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'file_info', 'access_level', 
                   'uploaded_by', 'download_count', 'is_active', 'created_at']
    list_filter = ['document_type', 'access_level', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['file_size', 'download_count', 'file_preview']
    
    fieldsets = (
        ('Información del documento', {
            'fields': ('title', 'description', 'file', 'file_preview')
        }),
        ('Configuración', {
            'fields': ('document_type', 'access_level', 'is_active')
        }),
        ('Relaciones', {
            'fields': ('related_posts',),
            'classes': ('collapse',)
        }),
        ('Información adicional', {
            'fields': ('file_size', 'download_count'),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['related_posts']
    
    def file_info(self, obj):
        if obj.file:
            return format_html(
                '<strong>{}</strong><br/><small>{}</small>',
                obj.file.name.split('/')[-1],
                obj.get_file_size_display()
            )
        return "Sin archivo"
    file_info.short_description = 'Archivo'
    
    def file_preview(self, obj):
        if obj.file:
            if obj.document_type == 'img':
                return format_html(
                    '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                    obj.file.url
                )
            else:
                return format_html(
                    '<a href="{}" target="_blank">Descargar archivo</a>',
                    obj.file.url
                )
        return "Sin archivo"
    file_preview.short_description = 'Vista previa'
    
    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(BlogTemplate)
class BlogTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'posts_per_page', 'show_sidebar', 
                   'created_by', 'updated_at']
    list_filter = ['is_active', 'show_sidebar', 'show_categories', 'show_tags']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Información básica', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Contenido del template', {
            'fields': ('header_content', 'footer_content', 'sidebar_content'),
            'classes': ('collapse',)
        }),
        ('Colores y estilos', {
            'fields': ('primary_color', 'secondary_color', 'background_color', 'text_color'),
            'classes': ('collapse',)
        }),
        ('Configuración de layout', {
            'fields': ('posts_per_page', 'show_sidebar', 'show_categories', 'show_tags'),
        }),
        ('CSS personalizado', {
            'fields': ('custom_css',),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author_name', 'post', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['author_name', 'author_email', 'content']
    readonly_fields = ['post_link']
    
    fieldsets = (
        ('Información del comentario', {
            'fields': ('author_name', 'author_email', 'content')
        }),
        ('Post relacionado', {
            'fields': ('post', 'post_link')
        }),
        ('Moderación', {
            'fields': ('is_approved',)
        })
    )
    
    def post_link(self, obj):
        if obj.post:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.post.get_absolute_url(),
                obj.post.title
            )
        return "N/A"
    post_link.short_description = 'Ver post'
    
    actions = ['approve_comments', 'unapprove_comments']
    
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} comentarios aprobados.')
    approve_comments.short_description = 'Aprobar comentarios seleccionados'
    
    def unapprove_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} comentarios desaprobados.')
    unapprove_comments.short_description = 'Desaprobar comentarios seleccionados'

# Personalización del admin site
admin.site.site_header = 'Administración del Blog'
admin.site.site_title = 'Blog Admin'
admin.site.index_title = 'Panel de administración'
