document.addEventListener('DOMContentLoaded', function() {
    // Protección adicional contra CSRF
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    // Función para confirmar logout - ÚNICA VERSIÓN
    window.confirmLogout = function(event) {
        event.preventDefault();
        
        // Verificar que el token CSRF esté presente
        if (!csrfToken) {
            console.error('Token CSRF no encontrado');
            return false;
        }
        
        // Confirmar logout
        if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
            document.getElementById('logout-form').submit();
        }
        
        return false;
    };
    
    // Protección adicional: verificar integridad del formulario de logout
    const logoutForm = document.getElementById('logout-form');
    if (logoutForm) {
        logoutForm.addEventListener('submit', function(e) {
            const formToken = this.querySelector('[name=csrfmiddlewaretoken]')?.value;
            
            // Verificar que el token no haya sido modificado
            if (!formToken || formToken !== csrfToken) {
                console.error('Token CSRF inválido o modificado');
                e.preventDefault();
                alert('Error de seguridad. Por favor, recarga la página.');
                return false;
            }
        });
    }
    
    // Confirmación específica para formularios de eliminación de archivos
    const deleteFileForms = document.querySelectorAll('form[action*="eliminar"], form.delete-form');
    deleteFileForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('¿Estás completamente seguro de que deseas eliminar este archivo? Esta acción no se puede deshacer.')) {
                e.preventDefault();
            }
        });
    });
    
    // Validación del formulario de cambio de contraseña
    const passwordForm = document.querySelector('#passwordModal form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', function(e) {
            const newPassword1 = document.getElementById('new_password1').value;
            const newPassword2 = document.getElementById('new_password2').value;
            
            if (newPassword1 !== newPassword2) {
                e.preventDefault();
                alert('Las contraseñas no coinciden. Por favor, verifica e intenta nuevamente.');
                return false;
            }
            
            if (newPassword1.length < 8) {
                e.preventDefault();
                alert('La contraseña debe tener al menos 8 caracteres.');
                return false;
            }
        });
    }
    
    // Función para mostrar mensajes dinámicos
    function showMessage(message, type = 'info') {
        const messagesContainer = document.getElementById('dynamic-messages');
        if (!messagesContainer) return;
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        messagesContainer.appendChild(alertDiv);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    // Función para actualizar el badge del rol
    function updateRoleBadge(userId, role) {
        const badge = document.getElementById(`role-badge-${userId}`);
        if (badge) {
            let badgeClass = '';
            let roleText = '';
            
            switch(role) {
                case 'admin':
                case 'administrador':
                    badgeClass = 'bg-danger';
                    roleText = 'Administrador';
                    break;
                case 'moderador':
                    badgeClass = 'bg-primary';
                    roleText = 'Moderador';
                    break;
                default:
                    badgeClass = 'bg-secondary';
                    roleText = 'Usuario';
            }
            
            badge.innerHTML = `<span class="badge ${badgeClass}">${roleText}</span>`;
        }
    }
    
    // Manejar envío de formularios de cambio de rol
    document.querySelectorAll('.role-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const userId = this.dataset.userId;
            const formData = new FormData(this);
            const newRole = formData.get('rol');
            
            // Confirmar cambio
            if (!confirm('¿Estás seguro de cambiar el rol de este usuario?')) {
                return;
            }
            
            // Deshabilitar el botón durante la petición
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            // Realizar petición AJAX
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showMessage(data.message, 'success');
                    updateRoleBadge(userId, data.nuevo_rol);
                } else {
                    showMessage(data.error || 'Error desconocido', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('Error al cambiar el rol. Por favor, intenta de nuevo.', 'danger');
            })
            .finally(() => {
                // Restaurar el botón
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHtml;
            });
        });
    });
    
    // Efecto de typing para mostrar información
    const infoItems = document.querySelectorAll('.info-item');
    infoItems.forEach((item, index) => {
        setTimeout(() => {
            item.style.opacity = '0';
            item.style.transform = 'translateX(-20px)';
            item.style.transition = 'all 0.5s ease';
            
            setTimeout(() => {
                item.style.opacity = '1';
                item.style.transform = 'translateX(0)';
            }, 100);
        }, index * 150);
    });
    
    // Protección contra clickjacking
    if (window.top !== window.self) {
        document.body.style.display = 'none';
        alert('Esta página no puede ser mostrada en un frame por razones de seguridad.');
    }
});

// Función para toggle del modo de edición
function toggleEditMode() {
    console.log('toggleEditMode ejecutado'); // Debug
    
    const viewMode = document.getElementById('view-mode');
    const editMode = document.getElementById('edit-mode');
    
    // Debug: verificar si los elementos existen
    console.log('viewMode encontrado:', viewMode);
    console.log('editMode encontrado:', editMode);
    
    if (!viewMode || !editMode) {
        console.error('Elementos view-mode o edit-mode no encontrados');
        alert('Error: No se encontraron los elementos necesarios para editar');
        return;
    }
    
    if (viewMode.style.display === 'none') {
        viewMode.style.display = 'block';
        editMode.style.display = 'none';
        console.log('Cambiado a modo vista');
    } else {
        viewMode.style.display = 'none';
        editMode.style.display = 'block';
        console.log('Cambiado a modo edición');
    }
}

// Función para manejar errores de CSRF
function handleCSRFError() {
    alert('Sesión expirada. Por favor, recarga la página e inicia sesión nuevamente.');
    window.location.reload();
}

// Interceptar respuestas de error CSRF
document.addEventListener('DOMContentLoaded', function() {
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        return originalFetch.apply(this, args)
            .then(response => {
                if (response.status === 403) {
                    response.text().then(text => {
                        if (text.includes('CSRF') || text.includes('Forbidden')) {
                            handleCSRFError();
                        }
                    });
                }
                return response;
            });
    };
});

