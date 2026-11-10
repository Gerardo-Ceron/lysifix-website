(function () {
    'use strict';

    // ==========================================
    // CONFIGURACIÓN GENERAL
    // ==========================================
    const apiBase = window.LYSIFIX_API_URL ||
        (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? (window.location.port === '3000' ? window.location.origin : 'http://127.0.0.1:5000')
            : 'https://lysifix-saas-oficial.onrender.com');

    const API_BASE_URL = apiBase.replace(/\/+$/, '');
    const esIngles = window.location.pathname.includes('/en/');
    const MAX_FILE_SIZE = 25 * 1024 * 1024;
    const EXTENSIONES_PERMITIDAS = ['csv', 'xlsx', 'xls'];

    window.LYSIFIX_API_URL = API_BASE_URL;

    const PLANES_LYSIFIX = {
        precio_basico_id: {
            nombre: esIngles ? 'Basic Plan' : 'Plan Básico',
            precio: '35.00'
        },
        precio_profesional_id: {
            nombre: esIngles ? 'Professional Plan' : 'Plan Profesional',
            precio: '45.00'
        },
        precio_avanzado_id: {
            nombre: esIngles ? 'Advanced Plan' : 'Plan Avanzado',
            precio: '75.00'
        },
        precio_premium_id: {
            nombre: esIngles ? 'Premium Plan' : 'Plan Premium',
            precio: '150.00'
        }
    };

    const ALIAS_PLANES_INGLES = {
        basic_plan_id: 'precio_basico_id',
        professional_plan_id: 'precio_profesional_id',
        advanced_plan_id: 'precio_avanzado_id',
        premium_plan_id: 'precio_premium_id'
    };

    // ==========================================
    // PROCESAMIENTO EXPRESS DE ARCHIVOS
    // ==========================================
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('emailFile');
    const botonProcesar = document.getElementById('btnProcesar');
    let archivoPendienteId = null;

    function obtenerExtension(file) {
        return file.name.split('.').pop().toLowerCase();
    }

    function validarArchivo(file) {
        if (!file) {
            return 'Selecciona un archivo antes de continuar.';
        }
        if (!EXTENSIONES_PERMITIDAS.includes(obtenerExtension(file))) {
            return 'Solo se admiten archivos .csv, .xlsx o .xls.';
        }
        if (file.size > MAX_FILE_SIZE) {
            return 'El archivo no puede superar los 25 MB.';
        }
        return '';
    }

    function mostrarMensajeArchivo(message, tipo = 'info') {
    Swal.fire({
        title: 'Lysifix',
        text: message,
        icon: tipo,
        background: '#0b1020',
        color: '#ffffff',
        confirmButtonText: 'Aceptar',
        confirmButtonColor: '#d4a017',
        customClass: {
            popup: 'lysifix-alert'
        }
    });
}

    function configurarSelectorDeArchivos() {
        if (!dropZone || !fileInput) {
            return;
        }

        dropZone.addEventListener('click', function (event) {
            if (event.target !== fileInput) {
                fileInput.click();
            }
        });

        fileInput.addEventListener('change', function () {
            const file = fileInput.files[0];
            const error = validarArchivo(file);

            if (error) {
                fileInput.value = '';
                archivoPendienteId = null;
                mostrarMensajeArchivo('❌ ' + error);
                return;
            }

            archivoPendienteId = null;
            mostrarMensajeArchivo('✅ Archivo cargado correctamente: ' + file.name);
            alSubirArchivoExitoso(file);
        });

        dropZone.addEventListener('dragover', function (event) {
            event.preventDefault();
            dropZone.style.borderColor = '#6366f1';
        });

        dropZone.addEventListener('dragleave', function () {
            dropZone.style.borderColor = '#334155';
        });

        dropZone.addEventListener('drop', function (event) {
            event.preventDefault();
            dropZone.style.borderColor = '#334155';

            const file = event.dataTransfer.files[0];
            const error = validarArchivo(file);

            if (error) {
                archivoPendienteId = null;
                mostrarMensajeArchivo('❌ ' + error);
                return;
            }

            fileInput.files = event.dataTransfer.files;
            archivoPendienteId = null;
            mostrarMensajeArchivo('✅ Archivo arrastrado correctamente: ' + file.name);
            alSubirArchivoExitoso(file);
        });
    }

    async function procesarArchivoExpress(event) {
        event.preventDefault();

        const file = fileInput.files[0];
        const validationError = validarArchivo(file);

        if (validationError) {
            mostrarMensajeArchivo('❌ ' + validationError);
            return;
        }

        const formData = new FormData();
        formData.append('file', file, file.name);
        botonProcesar.disabled = true;

        const textoOriginal = botonProcesar.textContent;
        botonProcesar.textContent = 'Procesando...';

        try {
        const response = await fetch('https://lysifix-saas-oficial.onrender.com/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let detalle = 'El servidor no pudo procesar el archivo.';

                try {
                    const errorData = await response.json();
                    detalle = errorData.error || errorData.detail || detalle;
                } catch (_) {
                    // La respuesta puede no ser JSON.
                }

                throw new Error(detalle);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const downloadLink = document.createElement('a');
            mostrarMensajeArchivo(
                `✅ Optimización completada Has recibido una muestra gratuita de 5 registros.¿Necesitas procesar el archivo completo? Nuestros planes premium te permiten optimizar miles de registros en minutos.`,
                'success'
            );
            downloadLink.href = url;
            downloadLink.download = 'Lysifix_Express_' + file.name;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            downloadLink.remove();
            window.URL.revokeObjectURL(url);

           
        } catch (error) {
            console.error('Error al procesar el archivo:', error);
            mostrarMensajeArchivo('❌ ' + error.message);
        } finally {
            botonProcesar.disabled = false;
            botonProcesar.textContent = textoOriginal;
        }
    }

    function configurarProcesamientoExpress() {
        if (botonProcesar && fileInput) {
            botonProcesar.addEventListener('click', procesarArchivoExpress);
        }
    }

    // ==========================================
    // PAGO CON PAYPAL
    // ==========================================
    function obtenerMensajeErrorPago() {
        return esIngles
            ? 'There was an error processing your PayPal payment.'
            : 'Hubo un error al procesar tu pago con PayPal.';
    }

    async function guardarArchivoPendiente() {
        const archivo = fileInput && fileInput.files[0];
        const error = validarArchivo(archivo);
        if (error) {
            throw new Error(esIngles
                ? 'Select a valid file before paying.'
                : error);
        }
        if (archivoPendienteId) {
            return archivoPendienteId;
        }

        const formData = new FormData();
        formData.append('file', archivo, archivo.name);
        const response = await fetch(API_BASE_URL + '/api/archivos-pendientes', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok || result.status !== 'success') {
            throw new Error(result.detail || result.message || 'No se pudo guardar el archivo.');
        }
        archivoPendienteId = result.file_id;
        return archivoPendienteId;
    }

    async function iniciarPago(planId) {
        const planIdCanonico = ALIAS_PLANES_INGLES[planId] || planId;
        const planSeleccionado = PLANES_LYSIFIX[planIdCanonico];
        const seccionPago = document.getElementById('paypal-checkout-section');
        const contenedorBotones = document.getElementById('paypal-button-container');

        if (!planSeleccionado || !seccionPago || !contenedorBotones) {
            console.error('No se pudo iniciar PayPal: plan o contenedor no válido.', planId);
            alert(esIngles ? 'The selected plan is not available.' : 'El plan seleccionado no está disponible.');
            return;
        }

        if (!window.paypal || typeof window.paypal.Buttons !== 'function') {
            console.error('El SDK de PayPal no está disponible.');
            alert(esIngles
                ? 'PayPal is temporarily unavailable. Please try again.'
                : 'PayPal no está disponible temporalmente. Intenta de nuevo.');
            return;
        }

        let fileId;
        try {
            fileId = await guardarArchivoPendiente();
        } catch (error) {
            console.error('No se pudo guardar el archivo para el pago:', error);
            alert(error.message);
            return;
        }

        seccionPago.style.display = 'block';
        seccionPago.scrollIntoView({ behavior: 'smooth' });
        contenedorBotones.replaceChildren();

        let capturedOrderId = '';
        window.paypal.Buttons({
            style: {
                layout: 'vertical',
                color: 'gold',
                shape: 'rect',
                label: 'pay'
            },
            createOrder: function (data, actions) {
                return actions.order.create({
                    purchase_units: [{
                        description: `Lysifix - ${planSeleccionado.nombre}`,
                        amount: {
                            currency_code: 'USD',
                            value: planSeleccionado.precio
                        }
                    }]
                });
            },
            onApprove: function (data, actions) {
                return actions.order.capture()
                    .then(function (orderData) {
                        if (orderData.status !== 'COMPLETED') {
                            throw new Error('PayPal no confirmó la orden.');
                        }
                        capturedOrderId = orderData.id;

                        contenedorBotones.innerHTML = `<p>${
                            esIngles
                                ? 'Payment approved. Processing your request...'
                                : 'Pago aprobado. Procesando tu solicitud...'
                        }</p>`;

                        const inputEmail = document.getElementById('input-email-usuario');
                        return fetch(API_BASE_URL + '/api/verificar_pago_y_procesar', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                email: inputEmail ? inputEmail.value : 'anonimo',
                                plan: planIdCanonico,
                                order_id: orderData.id,
                                file_id: fileId
                            })
                        });
                    })
                    .then(function (response) {
                        return response.json().then(function (result) {
                            if (!response.ok || result.status !== 'success') {
                                throw new Error(result.message || 'El servidor no pudo registrar el pago.');
                            }

                            esperarResultado(capturedOrderId, contenedorBotones);
                        });
                    });
            },
            onCancel: function () {
                console.info('El usuario canceló el pago de PayPal.');
            },
            onError: function (error) {
                const mensajeError = obtenerMensajeErrorPago();
                console.error('Error en la pasarela de PayPal:', error);
                contenedorBotones.innerHTML = `<p>${mensajeError}</p>`;
                alert(mensajeError);
            }
        }).render('#paypal-button-container').catch(function (error) {
            const mensajeError = obtenerMensajeErrorPago();
            console.error('No se pudo mostrar el botón de PayPal:', error);
            alert(mensajeError);
        });
    }

    function esperarResultado(orderId, contenedorBotones) {
        const limite = Date.now() + 5 * 60 * 1000;
        const intervalo = window.setInterval(async function () {
            if (Date.now() > limite) {
                window.clearInterval(intervalo);
                contenedorBotones.innerHTML = `<p>${esIngles
                    ? 'Processing is taking longer than expected. Please try again later.'
                    : 'El procesamiento está tardando más de lo esperado. Intenta de nuevo más tarde.'
                }</p>`;
                return;
            }

            try {
                const response = await fetch(API_BASE_URL + '/api/estado_trabajo/' + encodeURIComponent(orderId));
                const trabajo = await response.json();
                if (trabajo.status === 'listo') {
                    window.clearInterval(intervalo);
                    contenedorBotones.innerHTML = `
                        <p>${esIngles ? 'Your file is ready.' : 'Tu archivo está listo.'}</p>
                        <a href="${API_BASE_URL}/api/descargar/${encodeURIComponent(trabajo.archivo_salida)}" download>
                            ${esIngles ? 'Download repaired file' : 'Descargar archivo reparado'}
                        </a>`;
                } else if (trabajo.status === 'error') {
                    window.clearInterval(intervalo);
                    contenedorBotones.innerHTML = `<p>${esIngles
                        ? 'The file could not be processed.'
                        : 'No se pudo procesar el archivo.'
                    }</p>`;
                }
            } catch (error) {
                console.error('Error consultando el estado del trabajo:', error);
            }
        }, 2000);
    }

    function alSubirArchivoExitoso(file) {
        window.nombreArchivoSubido = file.name;
        console.log('Archivo seleccionado para procesar:', window.nombreArchivoSubido);
    }

    // ==========================================
    // INICIALIZACIÓN Y FUNCIONES PÚBLICAS
    // ==========================================
    configurarSelectorDeArchivos();
    configurarProcesamientoExpress();

    window.iniciarPago = iniciarPago;
    window.initiatePayment = iniciarPago;
    window.alSubirArchivoExitoso = alSubirArchivoExitoso;
}());
