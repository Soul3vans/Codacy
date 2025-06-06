from django.urls import path
from . import views

urlpatterns = [
    # URLs públicas
    path('', views.inicio, name='inicio'),
    path('posts/', views.lista_posts, name='lista_posts'),
    path('post/<slug:slug>/', views.detalle_post, name='post_detalle'),
    
    # URLs para administradores y moderadores
    path('gestionar/', views.gestionar_posts, name='gestionar_posts'),
    path('crear-post/', views.crear_post, name='crear_post'),
    path('editar-post/<int:post_id>/', views.editar_post, name='editar_post'),
    path('posts/eliminar/<int:post_id>/', views.eliminar_post, name='eliminar_post'),
    path('archivos/', views.gestionar_archivos, name='gestionar_archivos'),
    path('archivos/eliminar/<int:archivo_id>/', views.eliminar_archivo_view, name='eliminar_archivo'),

]