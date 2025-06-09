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
    path('editar/<int:pk>/', views.editar_archivo, name='editar_archivo'),
    path('eliminar/<int:pk>/', views.eliminar_archivo, name='eliminar_archivo'),
    # Rutas para enlaces de interés
    path('gestionar-enlaces/', views.gestionar_enlaces, name='gestionar_enlaces'),
    path('api/enlaces/<int:enlace_id>/', views.obtener_enlace_ajax, name='obtener_enlace_ajax'),
]