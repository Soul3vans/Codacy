from django.urls import path
from . import views

urlpatterns = [
    
    # Página principal
    path('', views.home, name='home'),
    
    # Autenticación
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Perfil
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    
 
    # Administración
    path('admin/panel/', views.panel_admin, name='panel_admin'),
    path('admin/usuario/<int:user_id>/rol/', views.cambiar_rol_usuario_view, name='cambiar_rol_usuario'),
    path('admin/usuario/<int:user_id>/estado/', views.cambiar_estado_usuario_view, name='cambiar_estado_usuario'),
]