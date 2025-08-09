from django.urls import path, reverse_lazy
from django.contrib.auth.views import LogoutView
from apps.dashboard.views import inicio
from . import views

urlpatterns = [
    # Página principal
    path('', inicio, name='inicio'),
    # Autenticación
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # URLs para perfil de usuario
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/actualizar/', views.actualizar_perfil, name='editar_perfil'),
    path('perfil/cambiar_password/', views.cambiar_password, name='cambiar_password'),
    path('perfil/password_reset_request/', views.password_reset_request, name='password_reset_request'),
    path('perfil/password_reset_confirm/<str:uidb64>/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    # Administración
    path('admin/panel/', views.panel_admin, name='panel_admin'),
    path('admin/usuario/<int:user_id>/rol/', views.cambiar_rol_usuario_view, name='cambiar_rol_usuario'),
    path('admin/usuario/<int:user_id>/estado/', views.cambiar_estado_usuario_view, name='cambiar_estado_usuario'),
    # URL adicional para debugging
    path('admin/usuario/<int:user_id>/info/', views.debug_user_info, name='debug_user_info'),
    path('admin/usuarios/eliminar/<int:user_id>/info', views.eliminar_usuario, name='eliminar_usuario'),

]