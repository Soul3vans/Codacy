document.addEventListener('DOMContentLoaded', function() {
    // Protección adicional contra CSRF
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    // Función para confirmar logout
    window.confirmLogout = function(event) {
        // Verificar que el token CSRF esté presente
        if (!csrfToken) {
            console.error('Token CSRF no encontrado');
            event.preventDefault();
            return false;
        }
        
        // Opcional: confirmar logout
        if (!confirm('¿Estás seguro de que quieres cerrar sesión?')) {
            event.preventDefault();
            return false;
        }
        
        return true;
    };
    
    // Protección adicional: verificar integridad del formulario
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
    
    // Protección contra clickjacking
    if (window.top !== window.self) {
        document.body.style.display = 'none';
        alert('Esta página no puede ser mostrada en un frame por razones de seguridad.');
    }
});

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


document.querySelector('form').addEventListener('submit', function(e) {
        if (!confirm('¿Estás completamente seguro de que deseas eliminar este archivo? Esta acción no se puede deshacer.')) {
            e.preventDefault();
        }
    });