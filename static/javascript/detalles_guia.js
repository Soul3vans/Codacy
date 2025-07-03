//Muestra el textarea cuando se marque la opcion no
document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM Content Loaded'); // Para depuración

    var radios = document.querySelectorAll('input[name^="respuesta_"]');

    // Función para manejar la visibilidad y habilitación del campo de fundamentación
    function toggleFundamentacionBox(preguntaId, isNoSelected) {
        var box = document.getElementById('fundamentacion-box-' + preguntaId);
        var textarea = document.getElementById('fundamentacion_' + preguntaId);
        if (box) {
            if (isNoSelected) {
                box.style.display = 'block'; // Mostrar el campo
                if (textarea) textarea.removeAttribute('disabled');
            } else {
                box.style.display = 'none'; // Ocultar el campo
                if (textarea) {
                    textarea.setAttribute('disabled', 'disabled');
                    textarea.value = '';
                }
            }
        }
    }

    // Inicializar la visibilidad y habilitación al cargar la página
    radios.forEach(function (radio) {
        if (radio.checked) {
            var preguntaId = radio.getAttribute('data-pregunta-id');
            toggleFundamentacionBox(preguntaId, radio.value === 'no');
        }
    });

    // Escuchar cambios en los radio buttons
    radios.forEach(function (radio) {
        radio.addEventListener('change', function () {
            var preguntaId = this.getAttribute('data-pregunta-id');
            toggleFundamentacionBox(preguntaId, this.value === 'no');
            // Enviar respuesta individualmente al cambiar el radio
            const fundamentacionTextarea = document.getElementById(`fundamentacion_${preguntaId}`);
            if (this.value === 'no') {
                // Habilitar y enfocar el textarea, y disparar un evento input para que el usuario pueda escribir inmediatamente
                fundamentacionTextarea.removeAttribute('disabled');
                fundamentacionTextarea.focus();
  
            } else {
                // Limpiar y deshabilitar el textarea si se selecciona otra opción
                fundamentacionTextarea.value = '';
                fundamentacionTextarea.setAttribute('disabled', 'disabled');
            }
            sendResponse(preguntaId, this.value, fundamentacionTextarea ? fundamentacionTextarea.value : '');
        });
    });

    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const form = document.querySelector('#guia-form');
    // Asegúrate de que el formulario exista antes de intentar acceder a sus propiedades
    const pdfDownloadUrl = form ? form.dataset.pdfUrl : null; 

    if (!form) {
        console.error('Formulario con ID "guia-form" no encontrado!');
        return; // Detener la ejecución si el formulario no se encuentra
    }

    // Función para enviar una única respuesta (usada por cambios individuales)
    function sendResponse(questionNumber, responseValue, fundamentacionValue) {
        const url = `/guia/guardar_respuesta/${form.dataset.guiaPk}/`;
        const data = {
            numero_pregunta: Number(questionNumber),
            respuesta: responseValue,
            fundamentacion: fundamentacionValue
        };

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Mostrar mensaje visual de éxito (puedes personalizar esto)
                //showTemporaryMessage('Respuesta guardada', 'success', questionNumber);
            } else {
                showTemporaryMessage(data.message || 'Hubo un error al guardar la respuesta.', 'danger', questionNumber);
            }
        })
        .catch(error => {
            showTemporaryMessage('Error de red o del servidor al guardar la respuesta.', 'danger', questionNumber);
        });
    }

    // Función para mostrar mensajes temporales junto a la pregunta
    function showTemporaryMessage(message, type, preguntaId) {
        let questionItem = document.querySelector(`.question-item[data-question-id="${preguntaId}"]`);
        if (!questionItem) return;
        let msgDiv = questionItem.querySelector('.temp-msg');
        if (!msgDiv) {
            msgDiv = document.createElement('div');
            msgDiv.className = 'temp-msg';
            questionItem.appendChild(msgDiv);
        }
        msgDiv.textContent = message;
        msgDiv.className = `temp-msg alert alert-${type} mt-2 py-1 px-2`;
        setTimeout(() => {
            if (msgDiv) msgDiv.remove();
        }, 2000);
    }
    // Manejar el envío del formulario
    if (pdfDownloadUrl) {
        form.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevenir el envío normal del formulario

            // Aquí puedes agregar lógica para validar o procesar el formulario antes de enviar
            // Por ejemplo, podrías enviar las respuestas de cada pregunta

            // Redirigir al usuario a la URL de descarga del PDF
            window.location.href = pdfDownloadUrl;
        });
    }
    else {
        form.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevenir el envío normal del formulario

            // Aquí puedes agregar lógica para validar o procesar el formulario antes de enviar
            // Por ejemplo, podrías enviar las respuestas de cada pregunta

            // Redirigir al usuario a la lista de guías con mensaje de éxito
            const params = new URLSearchParams({
                msg: 'success',
                detail: 'Respuestas guardadas correctamente.'
            });
            window.location.href = '/guia/?' + params.toString();
        });
    }

    // Evento para el botón Guardar respuestas
    const guardarBtn = document.getElementById('guardar-todo-btn');
    if (guardarBtn) {
        guardarBtn.addEventListener('click', function () {
            // Recolectar todas las respuestas del formulario
            const preguntas = document.querySelectorAll('.question-item');
            let respuestas = [];
            preguntas.forEach(function (item) {
                const preguntaId = item.getAttribute('data-question-id');
                const checkedRadio = item.querySelector('input[type="radio"]:checked');
                const respuesta = checkedRadio ? checkedRadio.value : '';
                const fundamentacion = document.getElementById('fundamentacion_' + preguntaId)?.value || '';
                respuestas.push({
                    numero_pregunta: Number(preguntaId),
                    respuesta: respuesta,
                    fundamentacion: fundamentacion
                });
            });
            // Enviar todas las respuestas en un solo request
            fetch(`/guia/guardar_respuesta/${form.dataset.guiaPk}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify(respuestas)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    if (data.porcentaje_completado === 100) {
                        // Si está completa, abrir el PDF en una nueva pestaña
                        window.open(form.dataset.pdfUrl, '_blank');
                    } else {
                        // Si no está completa, redirigir a la lista de guías
                        window.location.href = '/guia/?msg=success&detail=Respuestas guardadas correctamente.';
                    }
                } else {
                    alert(data.message || 'Error al guardar las respuestas.');
                }
            })
            .catch(() => {
                alert('Error de red o del servidor al guardar las respuestas.');
            });
        });
    }
});