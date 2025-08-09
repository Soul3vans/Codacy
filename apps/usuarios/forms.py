from django import forms
from django.forms.widgets import Select
from django.contrib.auth.forms import UserCreationForm
from django.forms import ChoiceField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Archivo, Perfil, CedeChoice


class RegistroForm(UserCreationForm):
    """Formulario de Registro de Usuario"""
    email = forms.EmailField(required=True, label='Correo Electrónico')
    first_name = forms.CharField(max_length=30, required=True, label='Nombre')
    last_name = forms.CharField(max_length=30, required=True, label='Apellidos')
    telefono = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1 234 567 8900'
        }),
        required=False,
        label='Teléfono'
    )
    cede = ChoiceField(
        choices=[('', "Seleccionar Cede Universitaria")] +
        list(CedeChoice.choices),
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