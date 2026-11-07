(function () {
    'use strict';

    // ==========================================
    // CONFIGURACIÓN GENERAL
    // ==========================================
    const API_BASE_URL = 'https://lysifix-saas-oficial.onrender.com';
    const esIngles = window.location.pathname.includes('/en/');
    const MAX_FILE_SIZE = 25 * 1024 * 1024;
    const EXTENSIONES_PERMITIDAS = ['csv', 'xlsx', 'xls'];

    window.LYSIFIX_API_URL = API_BASE_URL;

    const PLANES_LYSIFIX = {
        precio_basico_id: { nombre: esIngles ? 'Basic Plan' : 'Plan Básico', precio: '35.00' },
        precio_profesional_id: { nombre: esIngles ? 'Professional Plan' : 'Plan Profesional', precio: '45.00' },
        precio_avanzado_id: { nombre: esIngles ? 'Advanced Plan' : 'Plan Avanzado', precio: '75.00' },
        precio_premium_id: { nombre: esIngles ? 'Premium Plan' : 'Plan Premium', precio: '150.00' }
    };

    const ALIAS_PLANES_INGLES = {
        basic_plan_id: 'precio_basico_id',
        professional_plan_id: 'precio_profesional_id',
        advanced_plan_id: 'precio_avanzado_id',
        premium_plan_id: 'precio_premium_id'
    };

    // ==========================================
    // VARIABLES GLOBALES DE FLUJO
    // ==========================================
    const botonProcesar = document.getElementById('btnProcesar');
    let archivoPendienteId = null;
    let archivoActual = null;
    let planSeleccionadoGlobal = 'precio_premium_id'; // Plan por defecto si no eligen uno arriba

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

    function mostrarMensajeArchivo(message) {
        if (typeof window.alert === 'function') {
            window.alert(message);
        }
    }

    function obtenerMensajeErrorPago() {
        return esIngles
            ? 'There was an error processing your PayPal payment.'
            : 'Hubo un error al procesar tu pago con PayPal.';
    }

    // ==========================================
    // ENLACE DE BOTONES DE PLANES (FLUJO PROFESIONAL)
    // ==========================================
    function configurarBotonesPlanes() {
        // Buscamos todos los botones de "Buy with" en tu HTML de las tarjetas
        const botonesCompra = document.querySelectorAll('.plan-card button, [id*="buy-button"], .btn-plan, .pricing-button');
        
        botonesCompra.forEach(boton => {
            boton.addEventListener('click', function (event) {
                event.preventDefault();
                
                // Intentamos capturar el ID del plan desde algún atributo o inferimos uno
                const idAtributo = boton.getAttribute('data-plan-id') || boton.id;
                if (idAtributo && PLANES_LYSIFIX[idAtributo]) {
                    planSeleccionadoGlobal = idAtributo;
                } else if (ALIAS_PLANES_INGLES[idAtributo]) {
                    planSeleccionadoGlobal = ALIAS_PLANES_INGLES[idAtributo];
                }

                // 1. SCROLL SUAVE: Bajamos al cliente de inmediato a la zona azul de arrastre
                const zonaCarga = document.getElementById('dropZone') || document.getElementById('drop-zone') || document.querySelector('.dropzone');
                if (zonaCarga) {
                    zonaCarga.scrollIntoView({ behavior: 'smooth' });
                }

                // 2. MENSAJE PROFESIONAL: Le pedimos amablemente que cargue su archivo para avanzar
                const statusInstruction = document.getElementById("paypal-status-instruction");
                if (statusInstruction) {
                    statusInstruction.innerHTML = esIngles 
                        ? "Please upload or drag your Excel file here to activate checkout." 
                        : "Por favor, sube o arrastra tu archivo Excel aquí para activar el pago seguro.";
                    statusInstruction.style.color = "#03adfa";
                    statusInstruction.style.display = "block";
                }
            });
        });
    }

    // ==========================================
    // SELECTOR Y CARGA DE ARCHIVOS
    // ==========================================
    function configurarSelectorDeArchivos() {
        const fileInput = document.getElementById('emailFile') || document.getElementById('file-input');
        const dropZone = document.getElementById('dropZone') || document.getElementById('drop-zone') || document.querySelector('.dropzone');

        if (!fileInput) {
            console.error("Error crítico: No se encontró el input de archivo en el HTML.");
            return;
        }

        if (dropZone) {
            dropZone.style.cursor = 'pointer';
            dropZone.addEventListener('click', function (event) {
                if (event.target !== fileInput) {
                    fileInput.click();
                }
            });
        }

        fileInput.addEventListener('change', function () {
            if (!fileInput.files || fileInput.files.length === 0) return;
            const file = fileInput.files[0];

            archivoPendienteId = null;
            archivoActual = file; 
            
            mostrarMensajeArchivo('✅ Archivo cargado correctamente: ' + file.name);
            alSubirArchivoExitoso(file);

            const statusInstruction = document.getElementById("paypal-status-instruction");
            const buttonContainer = document.getElementById("paypal-button-container");
            const seccionCheckout = document.getElementById('lysifix-paypal-checkout');

            if (statusInstruction) {
                statusInstruction.innerHTML = esIngles 
                    ? "File uploaded successfully! Please complete your secure payment below." 
                    : "¡Archivo cargado con éxito! Por favor, completa tu pago seguro abajo.";
                statusInstruction.style.color = "#4ade80";
            }
                
            // DESPERTAR CHEKOUT: Hacemos visible el recuadro de PayPal e iniciamos los botones
            if (seccionCheckout) {
                seccionCheckout.style.display = "block";
                seccionCheckout.scrollIntoView({ behavior: 'smooth' });
            }

            if (buttonContainer) {
                buttonContainer.style.display = "block";  
                // Llamamos a PayPal solo AHORA que el archivo existe en memoria global
                iniciarPago(planSeleccionadoGlobal); 
            }
        });
    }

    function alSubirArchivoExitoso(file) {
        window.nombreArchivoSubido = file.name;
        console.log('Archivo seleccionado para procesar:', window.nombreArchivoSubido);
    }

    // ==========================================
    // PROCESAMIENTO EXPRESS (DIRECTO)
    // ==========================================
    async function procesarArchivoExpress(event) {
        if (event) event.preventDefault();

        const file = archivoActual || (document.getElementById('emailFile') && document.getElementById('emailFile').files[0]);
        const validationError = validarArchivo(file);

        if (validationError) {
            mostrarMensajeArchivo('❌ ' + validationError);
            return;
        }

        const formData = new FormData();
        formData.append('file', file, file.name);
        if (botonProcesar) botonProcesar.disabled = true;

        const textoOriginal = botonProcesar ? botonProcesar.textContent : 'Procesar';
        if (botonProcesar) botonProcesar.textContent = 'Procesando...';

        try {
            const response = await fetch(API_BASE_URL + '/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('El servidor no pudo procesar el archivo.');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const downloadLink = document.createElement('a');

            downloadLink.href = url;
            downloadLink.download = 'Lysifix_Express_' + file.name;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            downloadLink.remove();
            window.URL.revokeObjectURL(url);

            mostrarMensajeArchivo('✅ Procesamiento completado. La descarga ha iniciado.');
        } catch (error) {
            console.error('Error al procesar el archivo:', error);
            mostrarMensajeArchivo('❌ ' + error.message);
        } finally {
            if (botonProcesar) {
                botonProcesar.disabled = false;
                botonProcesar.textContent = textoOriginal;
            }
        }
    }

    function configurarProcesamientoExpress() {
        if (botonProcesar) {
            botonProcesar.addEventListener('click', procesarArchivoExpress);
        }
    }

    // ==========================================
    // PASARELA DE COBRO PAYPAL Y BACKEND
    // ==========================================
    async function guardarArchivoPendiente() {
        const fileInput = document.getElementById('emailFile') || document.getElementById('file-input');
        const archivo = archivoActual || (fileInput && fileInput.files[0]);
        
        const error = validarArchivo(archivo);
        if (error) {
            throw new Error(esIngles ? 'Select a valid file before paying.' : error);
        }
        if (archivoPendienteId) {
            return archivoPendienteId;
        }

        try {
            const formData = new FormData();
            formData.append('file', archivo, archivo.name);

            const response = await fetch(API_BASE_URL + '/upload-pending', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(esIngles
                    ? 'The file could not be uploaded.'
                    : 'No se pudo subir el archivo.');
            }

            const data = await response.json();
            archivoPendienteId = data.file_id || data.id || data.archivo_id;

            if (!archivoPendienteId) {
                throw new Error(esIngles
                    ? 'The server did not return a file ID.'
                    : 'El servidor no devolvió un identificador de archivo.');
            }

            return archivoPendienteId;
        } catch (error) {
            console.error('Error al guardar el archivo pendiente:', error);
            throw error;
        }
    }
    
    // ==========================================
    // INICIALIZACIÓN Y FUNCIONES PÚBLICAS
    // ==========================================
    configurarBotonesPlanes();
    configurarSelectorDeArchivos();
    configurarProcesamientoExpress();
async function iniciarPago(planId) {
        const planIdCanonico = ALIAS_PLANES_INGLES[planId] || planId;
        const planSeleccionado = PLANES_LYSIFIX[planIdCanonico] || PLANES_LYSIFIX['precio_premium_id'];
        const seccionPago = document.getElementById('lysifix-paypal-checkout');
        const contenedorBotones = document.getElementById('paypal-button-container');

        if (!planSeleccionado || !seccionPago || !contenedorBotones) {
            console.error('No se pudo iniciar PayPal: plan o contenedor no válido.', planId);
            return;
        }

        if (!window.paypal || typeof window.paypal.Buttons !== 'function') {
            console.error('El SDK de PayPal no está disponible.');
            return;
        }

        let fileId = "ID_PROCESADO_OK";
        try {
            if (archivoActual) {
                fileId = await guardarArchivoPendiente();
            }
        } catch (error) {
            fileId = "ID_PROCESADO_OK";
        }

        contenedorBotones.replaceChildren();

        let capturedOrderId = '';
        window.paypal.Buttons({
            style: { layout: 'vertical', color: 'gold', shape: 'rect', label: 'pay' },
            createOrder: function (data, actions) {
                if (!archivoActual) {
                    alert(esIngles ? 'Please upload a file before completing payment.' : 'Por favor, sube un archivo antes de completar el pago.');
                    return false;
                }
                return actions.order.create({
                    purchase_units: [{
                        description: `Lysifix - ${planSeleccionado.nombre}`,
                        amount: { currency_code: 'USD', value: planSeleccionado.precio }
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

                        contenedorBotones.innerHTML = `<p>${esIngles ? 'Payment approved. Processing...' : 'Pago aprobado. Procesando...'}</p>`;

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
            console.error('No se pudo mostrar el botón de PayPal:', error);
        });
    }

    function esperarResultado(orderId, contenedorBotones) {
        const limite = Date.now() + 5 * 60 * 1000;
        const intervalo = window.setInterval(async function () {
            if (Date.now() > limite) {
                window.clearInterval(intervalo);
                contenedorBotones.innerHTML = `<p>${esIngles ? 'Timeout. Try again later.' : 'Tiempo de espera agotado. Intenta de nuevo.'}</p>`;
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
                    contenedorBotones.innerHTML = `<p>${esIngles ? 'The file could not be processed.' : 'No se pudo procesar el archivo.'}</p>`;
                }
            } catch (error) {
                console.error('Error consultando el estado del trabajo:', error);
            }
        }, 2000);
    }
    // Exportamos la función al navegador de forma segura
    window.iniciarPago = iniciarPago;
    window.alSubirArchivoExitoso = alSubirArchivoExitoso;
})(); 