from django import forms
from django.forms.widgets import Select
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from apps.core.forms import ChoiceField as EmptyChoiceField
from django.core.exceptions import ValidationError
from .models import Post, Archivo, Categoria, Comentario, Perfil, CedeChoice

# FORMULARIO PERSONALIZADO DE REGISTRO
class RegistroForm(UserCreationForm):
     # Campos del Usuario
    email = forms.EmailField(required=True, label='Correo Electrónico')
    first_name = forms.CharField(max_length=30, required=True, label='Nombre')
    last_name = forms.CharField(max_length=30, required=True, label='Apellidos')
    
    # Campos del Perfil
    telefono = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1 234 567 8900'
        }),
        required=False,
        label='Teléfono'
    )
    cede = EmptyChoiceField(
        empty_label="Seleccionar Cede Universitaria",
        choices=CedeChoice.choices,
        widget=Select(attrs={"class": "form-control form-select"}),
        label="Cede",
        required=True,
    )
    cargo = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cargo que ocupa'
        }),
        required=True,
        label='Cargo'
    )
    recibir_notificaciones = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        initial=True,
        label='Recibir notificaciones por email'
    )

    class Meta:
        model = User
        fields = (
            "username", "first_name", "last_name", "email", 
            "password1", "password2", "cede", "cargo", "telefono",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar los widgets y clases CSS para campos de User
        for field_name in ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['class'] = 'form-control'
        
        # Personalizar labels y help texts
        self.fields['username'].help_text = 'Requerido. 150 caracteres o menos. Solo letras, dígitos y @/./+/-/_'
        self.fields['password1'].help_text = 'Tu contraseña debe tener al menos 8 caracteres.'
        self.fields['cede'].help_text = 'Cede a la que perteneces.'
        self.fields['cargo'].help_text = 'Cargo que ocupas.'
        self.fields['email'].help_text = 'Ingresa un correo electrónico válido.'

    def clean_email(self):
        """Validar que el email no esté ya registrado"""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este correo electrónico ya está registrado.')
        return email

    def save(self, commit=True):
        """Guardar usuario y crear perfil con los datos adicionales"""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        
        if commit:
            user.save()
            
            # Crear o actualizar el perfil con los datos adicionales
            perfil, created = Perfil.objects.get_or_create(user=user)
            perfil.telefono = self.cleaned_data.get('telefono', '')
            perfil.cede = self.cleaned_data.get('cede', '')
            perfil.cargo = self.cleaned_data.get('cargo', '')
            perfil.recibir_notificaciones = self.cleaned_data.get('recibir_notificaciones', True)
            perfil.perfil_publico = self.cleaned_data.get('perfil_publico', True)
            perfil.save()
            
        return user

class PerfilForm(forms.ModelForm):
    """
    Formulario para actualizar los campos adicionales del perfil.
    """
    cede = forms.ChoiceField(
        choices=[('', "Seleccionar Sede Universitaria")] + list(CedeChoice.choices),
        widget=Select(attrs={"class": "form-control form-select"}),
        label="Sede Universitaria",
        required=True,
    )
    class Meta:
        model = Perfil
        fields = ['telefono', 'cede', 'cargo', 'recibir_notificaciones', 'firma_digital']
        widgets = {
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 234 567 8900'
            }),
            'cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa tu cargo'
            }),
            'recibir_notificaciones': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'firma_digital': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #for field in self.fields.values():
        #self.fields['cede'].widget = Select(attrs={"class": "form-control form-select"})
    

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