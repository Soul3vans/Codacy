from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.home_view, name='home'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    path('panel-admin/', views.panel_admin_view, name='panel_admin'),
    path('cambiar-rol/<int:user_id>/', views.cambiar_rol_usuario_view, name='cambiar_rol'),
]