//Muestra el textarea cuando se marque la opcion no
document.addEventListener('DOMContentLoaded', function () {
    // --- INICIO: Lógica de inicialización y visibilidad de campos ---
    // Al cargar el DOM, busca todos los radios de respuestas y ajusta la visibilidad del campo de fundamentación
    var radios = document.querySelectorAll('input[name^="respuesta_"]');

    // Muestra u oculta el campo de fundamentación si se selecciona la opcion "no"
    function toggleFundamentacionBox(preguntaId, isNoSelected) {
        var box = document.getElementById('fundamentacion-box-' + preguntaId);
        var textarea = document.getElementById('fundamentacion_' + preguntaId);
        if (box) {
            if (isNoSelected) {
                box.style.display = 'block';
                if (textarea) textarea.removeAttribute('disabled');
            } else {
                box.style.display = 'none';
                if (textarea) {
                    textarea.setAttribute('disabled', 'disabled');
                    textarea.value = '';
                }
            }
        }
    }

    // Inicializa la visibilidad de los campos de fundamentación según el valor seleccionado
    radios.forEach(function (radio) {
        if (radio.checked) {
            var preguntaId = radio.getAttribute('data-pregunta-id');
            toggleFundamentacionBox(preguntaId, radio.value === 'no');
        }
    });

    // Escucha cambios en los radios y actualiza la visibilidad y envía la respuesta
    radios.forEach(function (radio) {
        radio.addEventListener('change', function () {
            var preguntaId = this.getAttribute('data-pregunta-id');
            toggleFundamentacionBox(preguntaId, this.value === 'no');
            // Enviar respuesta individualmente al cambiar el radio
            const fundamentacionTextarea = document.getElementById(`fundamentacion_${preguntaId}`);
            if (this.value === 'no') {
                fundamentacionTextarea.removeAttribute('disabled');
                fundamentacionTextarea.focus();
            } else {
                fundamentacionTextarea.value = '';
                fundamentacionTextarea.setAttribute('disabled', 'disabled');
            }
            sendResponse(preguntaId, this.value, fundamentacionTextarea ? fundamentacionTextarea.value : '');
        });
    });
    // --- FIN: Lógica de inicialización y visibilidad de campos ---

    // --- INICIO: Función fetch con timeout ---
    /**
     * Realiza una petición fetch con timeout
     * @param {string} url - URL a la que hacer la petición
     * @param {object} options - Opciones para fetch
     * @param {number} timeout - Tiempo máximo en ms (default: 8000ms)
     * @returns {Promise} Promesa que se rechaza si hay timeout
     */
    function fetchWithTimeout(url, options = {}, timeout = 8000) {
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                reject(new Error('Tiempo de espera agotado. Por favor verifica tu conexión e intenta nuevamente.'));
            }, timeout);

            fetch(url, options)
                .then(response => {
                    clearTimeout(timer);
                    resolve(response);
                })
                .catch(err => {
                    clearTimeout(timer);
                    reject(err);
                });
        });
    }
    // --- FIN: Función fetch con timeout ---

    // --- INICIO: Manejo de envío de respuestas individuales ---
    // --- DEBUG: Descomentar funciones
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const form = document.querySelector('#guia-form');
    const pdfDownloadUrl = form ? form.dataset.pdfUrl : null; 

    if (!form) {
        console.error('Formulario con ID "guia-form" no encontrado!');
        return; // Detener la ejecución si el formulario no se encuentra
    }

    // Envía una respuesta individual al backend
    function sendResponse(questionNumber, responseValue, fundamentacionValue) {
        const url = `/guia/guardar_respuesta/${form.dataset.guiaPk}/`;
        const data = {
            numero_pregunta: Number(questionNumber),
            respuesta: responseValue,
            fundamentacion: fundamentacionValue
        };

        fetchWithTimeout(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(data)
        }, 8000) // Timeout de 8 segundos
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                //showTemporaryMessage('Respuesta guardada correctamente.', 'success', questionNumber);
            } else {
                showTemporaryMessage(data.message || 'Hubo un error al guardar la respuesta.', 'danger', questionNumber);
            }
        })
        .catch(error => {
            const errorMsg = error.message || 'Error de red o del servidor al guardar la respuesta.';
            showTemporaryMessage(errorMsg, 'danger', questionNumber);
            console.error('Error en sendResponse:', error);
        })
        .finally(() => {
            hideLoadingSpinner(); // Asegurar que el spinner siempre se oculta
        });
    }
    // --- FIN: Manejo de envío de respuestas individuales ---

    // --- INICIO: Mensajes temporales junto a la pregunta ---
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
    // --- FIN: Mensajes temporales ---

    // --- INICIO: Manejo del envío del formulario completo (descarga PDF o redirección) ---
    if (pdfDownloadUrl) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            // Redirige a la descarga del PDF
            window.location.href = pdfDownloadUrl;
        });
    }
    else {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            // Redirige a la lista de guías con mensaje de éxito
            const params = new URLSearchParams({
                msg: 'success',
                detail: 'Respuestas guardadas correctamente.'
            });
            window.location.href = '/guia/?' + params.toString();
        });
    }
    // --- FIN: Manejo del envío del formulario completo ---

    // --- INICIO: Animación de carga tipo spinner ---
    function showLoadingSpinner() {
        if (document.getElementById('customLoadingSpinner')) return;
        const spinner = document.createElement('div');
        spinner.id = 'customLoadingSpinner';
        spinner.innerHTML = `
        <div class="spinner-overlay">
            <div class="lds-dual-ring"></div>
            <p class="mt-3">Procesando, por favor espere...</p>
        </div>`;
        document.body.appendChild(spinner);
    }
    function hideLoadingSpinner() {
        const spinner = document.getElementById('customLoadingSpinner');
        if (spinner) spinner.remove();
    }
    // --- FIN: Animación de carga ---

    // --- INICIO: Guardar todas las respuestas y mostrar modal de finalización ---
    const guardarBtn = document.getElementById('guardar-todo-btn');
    if (guardarBtn) {
        guardarBtn.addEventListener('click', function () {
            showLoadingSpinner();
            // Recolecta todas las respuestas del formulario
            const preguntas = document.querySelectorAll('.question-item');
            let respuestas = [];
            let respondidas = 0;
            preguntas.forEach(function (item) {
                const preguntaId = item.getAttribute('data-question-id');
                const checkedRadio = item.querySelector('input[type="radio"]:checked');
                const respuesta = checkedRadio ? checkedRadio.value : '';
                if (['si', 'no', 'na'].includes(respuesta)) respondidas++;
                const fundamentacion = document.getElementById('fundamentacion_' + preguntaId)?.value || '';
                respuestas.push({
                    numero_pregunta: Number(preguntaId),
                    respuesta: respuesta,
                    fundamentacion: fundamentacion
                });
            });
            // Detecta si la guía está completa antes de enviar
            const totalPreguntas = preguntas.length;
            const guiaCompleta = respondidas === totalPreguntas && totalPreguntas > 0;
            if (guiaCompleta) showLoadingSpinner();
            // Envia todas las respuestas al backend
            fetchWithTimeout(`/guia/guardar_respuesta/${form.dataset.guiaPk}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify(respuestas)
            }, 15000) // Timeout más largo para guardar todo (15 segundos)
            .then(response => response.json())
            .then(data => {
                console.log('Respuesta del backend:', data);
                if (data.status === 'success') {
                    if (guiaCompleta) {
                        setTimeout(function() {
                            hideLoadingSpinner();
                            console.log('Mostrando modal de finalización...');
                            // Espera un pequeño delay para asegurar que el backend termine y el DOM esté listo
                            var completionModalEl = document.getElementById('completionModal');
                            if (!completionModalEl) {
                                console.error('No se encontró el modal en el DOM');
                                return;
                            }
                            var completionModal = new bootstrap.Modal(completionModalEl);
                            completionModal.show();
                            document.getElementById('reviewAnswersBtn').onclick = function() {
                                completionModal.hide();
                            };
                            document.getElementById('finishFormBtn').onclick = function() {
                                window.open(form.dataset.pdfUrl, '_blank');
                                setTimeout(function() {
                                    window.location.href = '/guia/mis-evaluaciones/?msg=success&detail=PDF generado correctamente.';
                                }, 1200);
                            };
                        }, 600); // spinner visible al menos 600ms
                    } else {
                        window.location.href = '/guia/?msg=success&detail=Respuestas guardadas correctamente.';
                    }
                } else {
                    alert(data.message || 'Error al guardar las respuestas.');
                }
            })
            .catch((error) => {
                alert(error.message || 'Error de red o del servidor al guardar las respuestas.');
                console.error('Error al guardar todo:', error);
            })
            .finally(() => {
                hideLoadingSpinner();
            });
        });
    }
    // --- FIN: Guardar todas las respuestas y mostrar modal de finalización ---

    // --- INICIO: CSS para el spinner ---
    const spinnerStyle = document.createElement('style');
    spinnerStyle.innerHTML = `
    .spinner-overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(255,255,255,0.7);
        z-index: 2000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .lds-dual-ring {
        display: inline-block;
        width: 64px;
        height: 64px;
    }
    .lds-dual-ring:after {
        content: " ";
        display: block;
        width: 46px;
        height: 46px;
        margin: 1px;
        border-radius: 50%;
        border: 6px solid #007bff;
        border-color: #007bff transparent #007bff transparent;
        animation: lds-dual-ring 1.2s linear infinite;
    }
    @keyframes lds-dual-ring {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    `;
    document.head.appendChild(spinnerStyle);
    // --- FIN CSS spinner ---

    // --- INICIO: Función para descargar PDF y preguntar al usuario ---
    window.descargarYPreguntarPDF = function(pdfUrl, redirigirTrasDescarga) {
        var form = document.getElementById('descargarPdfForm');
        if (!form) {
            form = document.createElement('form');
            form.id = 'descargarPdfForm';
            form.method = 'get';
            form.style.display = 'none';
            document.body.appendChild(form);
        }
        form.action = pdfUrl;
        form.submit();
        setTimeout(function() {
            if (confirm('¿Deseas revisar tus respuestas antes de terminar?')) {
                // Revisar respuestas: solo ocultar el formulario (no redirige)
                form.style.display = 'none';
            } else {
                // Terminar formulario: descargar PDF y redirigir
                window.open(pdfUrl, '_blank');
                if (redirigirTrasDescarga) {
                    setTimeout(function() {
                        window.location.href = '/guia/mis-evaluaciones/?msg=success&detail=PDF generado correctamente.';
                    }, 1200);
                }
            }
        }, 1200);
    };
    // --- FIN: Función para descargar PDF y preguntar al usuario ---
});