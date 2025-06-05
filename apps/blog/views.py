# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
import os
from .models import BlogPost, Document, BlogTemplate, Category, Tag, Comment
from .forms import CommentForm, DocumentForm

def is_moderator(user):
    """Verifica si el usuario es moderador"""
    return user.is_staff or user.groups.filter(name='Moderadores').exists()

class BlogListView(ListView):
    """Vista principal del blog"""
    model = BlogPost
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = BlogPost.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author', 'category').prefetch_related('tags')
        
        # Filtro por categoría
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Filtro por tag
        tag = self.request.GET.get('tag')
        if tag:
            queryset = queryset.filter(tags__slug=tag)
        
        # Búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(excerpt__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['tags'] = Tag.objects.all()
        context['featured_posts'] = BlogPost.objects.filter(
            status='published',
            is_featured=True,
            published_at__lte=timezone.now()
        )[:3]
        
        # Obtener template activo
        try:
            context['blog_template'] = BlogTemplate.objects.get(is_active=True)
        except BlogTemplate.DoesNotExist:
            context['blog_template'] = None
        
        return context

class BlogDetailView(DetailView):
    """Vista de detalle del post"""
    model = BlogPost
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return BlogPost.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        )
    
    def get_object(self):
        obj = super().get_object()
        # Incrementar contador de vistas
        BlogPost.objects.filter(pk=obj.pk).update(views_count=F('views_count') + 1)
        obj.refresh_from_db()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        
        # Comentarios aprobados
        context['comments'] = Comment.objects.filter(
            post=post,
            is_approved=True
        ).order_by('-created_at')
        
        # Formulario de comentarios
        context['comment_form'] = CommentForm()
        
        # Posts relacionados
        context['related_posts'] = BlogPost.objects.filter(
            status='published',
            category=post.category
        ).exclude(pk=post.pk)[:3]
        
        # Documentos relacionados
        context['related_documents'] = Document.objects.filter(
            related_posts=post,
            is_active=True,
            access_level='public'
        )
        
        # Template activo
        try:
            context['blog_template'] = BlogTemplate.objects.get(is_active=True)
        except BlogTemplate.DoesNotExist:
            context['blog_template'] = None
        
        return context

def add_comment(request, slug):
    """Añadir comentario a un post"""
    if request.method == 'POST':
        post = get_object_or_404(BlogPost, slug=slug, status='published')
        form = CommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.save()
            messages.success(request, 'Tu comentario ha sido enviado y está pendiente de moderación.')
        else:
            messages.error(request, 'Error al enviar el comentario. Verifica los datos.')
    
    return redirect('blog:post_detail', slug=slug)

def category_posts(request, slug):
    """Posts por categoría"""
    category = get_object_or_404(Category, slug=slug)
    posts = BlogPost.objects.filter(
        category=category,
        status='published',
        published_at__lte=timezone.now()
    )
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'blog/category_posts.html', {
        'category': category,
        'posts': page_obj,
        'page_obj': page_obj
    })

def tag_posts(request, slug):
    """Posts por tag"""
    tag = get_object_or_404(Tag, slug=slug)
    posts = BlogPost.objects.filter(
        tags=tag,
        status='published',
        published_at__lte=timezone.now()
    )
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'blog/tag_posts.html', {
        'tag': tag,
        'posts': page_obj,
        'page_obj': page_obj
    })

@login_required
@user_passes_test(is_moderator)
def document_list(request):
    """Lista de documentos para moderadores"""
    documents = Document.objects.all().select_related('uploaded_by')
    
    # Filtros
    doc_type = request.GET.get('type')
    if doc_type:
        documents = documents.filter(document_type=doc_type)
    
    access_level = request.GET.get('access')
    if access_level:
        documents = documents.filter(access_level=access_level)
    
    search = request.GET.get('search')
    if search:
        documents = documents.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'blog/document_list.html', {
        'documents': page_obj,
        'page_obj': page_obj,
        'document_types': Document.DOCUMENT_TYPES,
        'access_levels': Document.ACCESS_LEVELS
    })

@login_required
@user_passes_test(is_moderator)
def document_detail(request, pk):
    """Vista de detalle de documento para moderadores"""
    document = get_object_or_404(Document, pk=pk)
    
    return render(request, 'blog/document_detail.html', {
        'document': document
    })

@login_required
@user_passes_test(is_moderator)
def document_upload(request):
    """Subir nuevo documento"""
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            document.save()
            form.save_m2m()  # Para campos many-to-many
            messages.success(request, 'Documento subido exitosamente.')
            return redirect('blog:document_list')
        else:
            messages.error(request, 'Error al subir el documento. Verifica los datos.')
    else:
        form = DocumentForm()
    
    return render(request, 'blog/document_upload.html', {
        'form': form
    })

@login_required
@user_passes_test(is_moderator)
def document_edit(request, pk):
    """Editar documento existente"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Documento actualizado exitosamente.')
            return redirect('blog:document_detail', pk=document.pk)
        else:
            messages.error(request, 'Error al actualizar el documento.')
    else:
        form = DocumentForm(instance=document)
    
    return render(request, 'blog/document_edit.html', {
        'form': form,
        'document': document
    })

@login_required
@user_passes_test(is_moderator)
def document_delete(request, pk):
    """Eliminar documento"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        # Eliminar archivo físico si existe
        if document.file and os.path.isfile(document.file.path):
            os.remove(document.file.path)
        
        document.delete()
        messages.success(request, 'Documento eliminado exitosamente.')
        return redirect('blog:document_list')
    
    return render(request, 'blog/document_delete.html', {
        'document': document
    })

def download_document(request, pk):
    """Descargar documento (si tiene permisos)"""
    document = get_object_or_404(Document, pk=pk, is_active=True)
    
    # Verificar permisos de acceso
    if document.access_level == 'private' and not request.user.is_authenticated:
        raise Http404("Documento no encontrado")
    
    if document.access_level == 'restricted' and not is_moderator(request.user):
        raise Http404("No tienes permisos para acceder a este documento")
    
    # Verificar que el archivo existe
    if not document.file or not os.path.isfile(document.file.path):
        raise Http404("Archivo no encontrado")
    
    # Incrementar contador de descargas
    Document.objects.filter(pk=document.pk).update(download_count=F('download_count') + 1)
    
    # Servir archivo
    with open(document.file.path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{document.file.name}"'
        return response

@login_required
@user_passes_test(is_moderator)
def moderate_comment(request, comment_id):
    """Moderar comentario (aprobar/rechazar)"""
    if request.method == 'POST':
        comment = get_object_or_404(Comment, pk=comment_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            comment.is_approved = True
            comment.save()
            messages.success(request, 'Comentario aprobado.')
        elif action == 'reject':
            comment.delete()
            messages.success(request, 'Comentario eliminado.')
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'})

def search_posts(request):
    """Búsqueda AJAX de posts"""
    query = request.GET.get('q', '')
    
    if len(query) < 3:
        return JsonResponse({'results': []})
    
    posts = BlogPost.objects.filter(
        Q(title__icontains=query) |
        Q(content__icontains=query) |
        Q(excerpt__icontains=query),
        status='published',
        published_at__lte=timezone.now()
    )[:10]
    
    results = [{
        'title': post.title,
        'url': post.get_absolute_url(),
        'excerpt': post.excerpt[:100] + '...' if len(post.excerpt) > 100 else post.excerpt
    } for post in posts]
    
    return JsonResponse({'results': results})