from django import forms
from django.contrib.auth.models import User
from .models import Post, Archivo, Perfil, Categoria, Comentario

class PerfilForm(forms.ModelForm):
    """Formulario para editar el perfil del usuario"""
    
    class Meta:
        model = Perfil
        fields = ['avatar', 'bio', 'fecha_nacimiento', 'telefono', 'ciudad', 
                 'recibir_notificaciones', 'perfil_publico']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Cuéntanos algo sobre ti...'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 234 567 8900'
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tu ciudad'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'recibir_notificaciones': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'perfil_publico': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class PostForm(forms.ModelForm):
    """Formulario para crear y editar posts"""
    
    class Meta:
        model = Post
        fields = ['titulo', 'contenido', 'resumen', 'imagen_destacada', 
                 'categorias', 'publicado', 'destacado', 'meta_descripcion', 'meta_keywords']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título del post'
            }),
            'contenido': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'Escribe tu contenido aquí...'
            }),
            'resumen': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Resumen breve del post (opcional)',
                'maxlength': 300
            }),
            'imagen_destacada': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'categorias': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'publicado': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'destacado': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'meta_descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción para SEO (opcional)',
                'maxlength': 160
            }),
            'meta_keywords': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Palabras clave separadas por comas'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categorias'].queryset = Categoria.objects.filter(activa=True)

class ArchivoForm(forms.ModelForm):
    """Formulario para subir archivos"""
    
    class Meta:
        model = Archivo
        fields = ['archivo', 'descripcion', 'publico']
        widgets = {
            'archivo': forms.FileInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del archivo (opcional)'
            }),
            'publico': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class CategoriaForm(forms.ModelForm):
    """Formulario para gestionar categorías"""
    
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'color', 'icono', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la categoría'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la categoría'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'icono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'fas fa-tag (clase de FontAwesome)'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class ComentarioForm(forms.ModelForm):
    """Formulario para comentarios"""
    
    class Meta:
        model = Comentario
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escribe tu comentario...'
            }),
        }

class BuscarForm(forms.Form):
    """Formulario para búsquedas"""
    q = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar posts, usuarios...',
            'autocomplete': 'off'
        })
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(activa=True),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

class ActualizarPerfilForm(forms.ModelForm):
    """
    Formulario para actualizar perfil de usuario
    """
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu nombre'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Apellidos',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tus apellidos'
        })
    )
    
    email = forms.EmailField(
        required=True,
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tu@email.com'
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.user:
            if User.objects.filter(email=email).exclude(id=self.user.id).exists():
                raise ValidationError('Este correo electrónico ya está en uso.')
        return email