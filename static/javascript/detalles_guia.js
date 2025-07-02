//Muestra el textarea cuando se marque la opcion no
document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM Content Loaded'); // Para depuración

    var radios = document.querySelectorAll('input[name^="respuesta_"]');

    // Función para manejar la visibilidad del campo de fundamentación
    function toggleFundamentacionBox(preguntaId, isNoSelected) {
        var box = document.getElementById('fundamentacion-box-' + preguntaId);
        if (box) {
            if (isNoSelected) {
                box.style.display = 'block'; // Mostrar el campo
            } else {
                box.style.display = 'none'; // Ocultar el campo
            }
        }
    }

    // Inicializar la visibilidad al cargar la página
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
        const url = `/guia/guardar_respuesta/${form.dataset.guiaPk}/`; // Usar una URL dinámica si es necesario
        // O si la acción del formulario ya es la correcta:
        // const url = form.action; // Si el action del form es el endpoint correcto

        const data = {
            numero_pregunta: Number(questionNumber), // <-- aseguramos que sea número
            respuesta: responseValue,
            fundamentacion: fundamentacionValue
        };

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || 'Error desconocido del servidor'); });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                console.log('Respuesta guardada individualmente:', data.message);
                updateProgressBar(data.porcentaje_completado, data.preguntas_respondidas, data.total_preguntas);
                updateCompletionIndicator(questionNumber, responseValue);

                if (data.porcentaje_completado === 100) {
                    showCompletionModal();
                }
            } else {
                console.error('Error al guardar respuesta individual:', data.message);
                showMessage('danger', 'Hubo un error al guardar la respuesta: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error de red o del servidor al guardar respuesta individual:', error);
            showMessage('danger', 'Error de conexión o del servidor al guardar la respuesta: ' + error.message);
        });
    }

    // Escuchar cambios en los textareas de fundamentación para enviar individualmente
    document.querySelectorAll('.question-item textarea[name^="fundamentacion_"]').forEach(textareaInput => {
        const questionId = textareaInput.id.replace('fundamentacion_', '');
        let timeout = null;
        textareaInput.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const selectedRadio = document.querySelector(`input[type="radio"][name="respuesta_${questionId}"]:checked`);
                const responseValue = selectedRadio ? selectedRadio.value : null;
                sendResponse(questionId, responseValue, this.value);
            }, 800); // Pequeño retraso para evitar envíos excesivos al escribir
        });
    });

    // --- Nueva función para mostrar el modal de completitud ---
    function showCompletionModal() {
        const completionModal = new bootstrap.Modal(document.getElementById('completionModal'));
        completionModal.show();

        document.getElementById('reviewAnswersBtn').onclick = function() {
            completionModal.hide();
        };

        document.getElementById('finishFormBtn').onclick = function() {
            completionModal.hide();
            if (pdfDownloadUrl) {
                window.location.href = pdfDownloadUrl;
            } else {
                showMessage('warning', 'URL de descarga de PDF no disponible.');
            }
        };
    }

    // Función para actualizar la barra de progreso
    function updateProgressBar(porcentaje, respondidas, total) {
        const progressBar = document.querySelector('.progress-bar');
        const progressBarText = document.querySelector('.progress-bar-text');
        const questionsCountText = document.querySelector('.progress-header p');

        if (progressBar) {
            progressBar.style.width = porcentaje + '%';
            progressBar.setAttribute('aria-valuenow', porcentaje);
        }
        if (progressBarText) {
            progressBarText.textContent = porcentaje + '% Completado';
        }
        if (questionsCountText) {
            questionsCountText.textContent = `Preguntas respondidas: ${respondidas} de ${total}`;
        }
    }

    // Función para actualizar el indicador de completitud de la pregunta
    function updateCompletionIndicator(questionNumber, responseValue) {
        const questionDiv = document.querySelector(`.question-item[data-question-id="${questionNumber}"]`);
        if (questionDiv) {
            const completionIndicator = questionDiv.querySelector('.completion-indicator');
            if (['si', 'no', 'na'].includes(responseValue)) {
                questionDiv.classList.add('completed');
                if (completionIndicator && !completionIndicator.querySelector('.fas.fa-check')) {
                     completionIndicator.innerHTML = '<i class="fas fa-check"></i>';
                }
            } else {
                questionDiv.classList.remove('completed');
                if (completionIndicator) {
                    completionIndicator.innerHTML = '';
                }
            }
        }
    }

    // Función para mostrar mensajes temporales en la interfaz
    function showMessage(type, message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('alert', `alert-${type}`, 'mt-3', 'alert-dismissible', 'fade', 'show');
        messageDiv.setAttribute('role', 'alert');
        messageDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        form.prepend(messageDiv);
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getInstance(messageDiv);
            if (bsAlert) bsAlert.close();
            else messageDiv.remove();
        }, 10000); // El mensaje desaparece después de 10 segundos
    }

    // --- Lógica para el botón "Guardar respuestas" (envío de todas las respuestas) ---
    // Función para recolectar todas las respuestas del formulario
    function collectAllResponses() {
        const allResponses = [];
        document.querySelectorAll('.question-item').forEach(questionDiv => {
            const questionId = questionDiv.dataset.questionId;
            const selectedRadio = questionDiv.querySelector(`input[type="radio"][name="respuesta_${questionId}"]:checked`);
            const responseValue = selectedRadio ? selectedRadio.value : null;
            const fundamentacionTextarea = questionDiv.querySelector(`textarea[name="fundamentacion_${questionId}"]`);
            const fundamentacionValue = fundamentacionTextarea ? fundamentacionTextarea.value : '';

            // Siempre incluir la pregunta si tiene ID, incluso si no está respondida,
            // para que el backend pueda procesar el estado de todas las preguntas.
            allResponses.push({
                numero_pregunta: Number(questionId),
                respuesta: responseValue,
                fundamentacion: fundamentacionValue
            });
        });
        return allResponses;
    }

    // Listener para el botón "Guardar respuestas"
    const guardarTodoBtn = document.getElementById('guardar-todo-btn');
    if (guardarTodoBtn) {
        guardarTodoBtn.addEventListener('click', function(e) {
            e.preventDefault(); // Prevenir el comportamiento predeterminado del botón
            console.log("Botón 'Guardar respuestas' clickeado. Iniciando guardado de todas las respuestas por AJAX.");

            const allResponses = collectAllResponses();
            
            // Si el formulario no tiene preguntas o no se ha respondido nada, se puede mostrar un mensaje
            if (allResponses.length === 0) {
                showMessage('info', 'No hay respuestas para guardar.');
                return;
            }

            fetch(`/guia/guardar_respuesta/${form.dataset.guiaPk}/`, { // Usar el endpoint correcto
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify(allResponses) // Enviar un array de respuestas
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message || 'Error desconocido del servidor'); });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    console.log('Todas las respuestas guardadas:', data.message);
                    updateProgressBar(data.porcentaje_completado, data.preguntas_respondidas, data.total_preguntas);
                    // Re-evaluar los indicadores de completitud para todas las preguntas
                    document.querySelectorAll('.question-item').forEach(questionDiv => {
                        const questionId = questionDiv.dataset.questionId;
                        const selectedRadio = questionDiv.querySelector(`input[type="radio"][name="respuesta_${questionId}"]:checked`);
                        const responseValue = selectedRadio ? selectedRadio.value : null;
                        updateCompletionIndicator(questionId, responseValue);
                    });

                    if (data.porcentaje_completado === 100) {
                        showCompletionModal();
                    } else {
                        showMessage('success', 'Respuestas guardadas correctamente.');
                    }
                } else {
                    console.error('Error al guardar todas las respuestas:', data.message);
                    showMessage('danger', 'Hubo un error al guardar todas las respuestas: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error de red o del servidor al guardar todas las respuestas:', error);
                showMessage('danger', 'Error de conexión o del servidor al guardar todas las respuestas: ' + error.message);
            });
        });
    }
});
