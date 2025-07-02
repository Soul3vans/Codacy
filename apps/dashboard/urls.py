from django.urls import path
from . import views

urlpatterns = [
    # URLs públicas
    path('', views.inicio, name='inicio'),
    # URLs para administradores y moderadores
    path('archivos/', views.gestionar_archivos, name='gestionar_archivos'),
    path('editar/<int:pk>/', views.editar_archivo, name='editar_archivo'),
    path('eliminar/<int:pk>/', views.eliminar_archivo, name='eliminar_archivo'),
    # Rutas para enlaces de interés
    path('gestionar-enlaces/', views.gestionar_enlaces, name='gestionar_enlaces'),
    path('api/enlaces/<int:enlace_id>/', views.obtener_enlace_ajax, name='obtener_enlace_ajax'),
]