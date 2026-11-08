(function () {
    'use strict';

const express = require('express');
const cors = require('cors');
const app = express();

// Configuración de CORS
app.use(cors({
  origin: 'http://127.0.0.1:5500', // Reemplaza exactamente por el origen de tu frontend
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Tus rutas van aquí abajo...
app.post('/chat', (req, res) => {
  // Código de tu endpoint
});

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
    let planSeleccionadoGlobal = 'precio_premium_id'; 

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

   // // FILTRO INTELIGENTE DE AVISOS: Bloquea avisos viejos de éxito y activa SweetAlert2
    function mostrarMensajeArchivo(message) {
        if (message.includes("Procesamiento completado") || message.includes("Archivo cargado correctamente") || message.includes("La descarga ha iniciado")) {
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: '¡Proceso Exitoso!',
                    text: message,
                    icon: 'success',
                    confirmButtonColor: '#03adfa'
                });
            }
            return;
        }

        // Si es cualquier otro mensaje o advertencia del sistema
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Aviso de Lysifix',
                text: message,
                icon: 'warning',
                confirmButtonColor: '#03adfa'
            });
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
        const botonesCompra = document.querySelectorAll('.plan-card button, [id*="buy-button"], .btn-plan, .pricing-button');
        
        botonesCompra.forEach(boton => {
            boton.addEventListener('click', function (event) {
                event.preventDefault();
                
                const idAtributo = boton.getAttribute('data-plan-id') || boton.id;
                if (idAtributo && PLANES_LYSIFIX[idAtributo]) {
                    planSeleccionadoGlobal = idAtributo;
                } else if (ALIAS_PLANES_INGLES[idAtributo]) {
                    planSeleccionadoGlobal = ALIAS_PLANES_INGLES[idAtributo];
                }

                const zonaCarga = document.getElementById('dropZone') || document.getElementById('drop-zone') || document.querySelector('.dropzone');
                if (zonaCarga) {
                    zonaCarga.scrollIntoView({ behavior: 'smooth' });
                }

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
            
            // Reemplazado por SweetAlert estético para el primer aviso de éxito de carga
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: esIngles ? 'File Uploaded!' : '¡Archivo Cargado!',
                    text: esIngles ? `Successfully loaded: ${file.name}` : `Se cargó correctamente el archivo: ${file.name}`,
                    icon: 'info',
                    confirmButtonColor: '#03adfa'
                });
            } else {
                mostrarMensajeArchivo('✅ Archivo cargado correctamente: ' + file.name);
            }
            
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
                
            if (seccionCheckout) {
                seccionCheckout.style.display = "block";
                seccionCheckout.scrollIntoView({ behavior: 'smooth' });
            }

            if (buttonContainer) {
                buttonContainer.style.display = "block";  
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
            // 1. Enviamos el archivo al servidor en Render
            const response = await fetch(API_BASE_URL + '/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Error al procesar el archivo en el servidor.');

            // 2. RECIBIR COMO BLOB BINARIO PURO (Esto evita el SyntaxError de "PK")
            const blobExcel = await response.blob();

            // 3. Forzar la descarga automática del archivo de 5 filas gratis
            const urlDescarga = window.URL.createObjectURL(blobExcel);
            const linkTemporal = document.createElement('a');
            linkTemporal.href = urlDescarga;
            linkTemporal.download = 'Muestra_Gratis_' + file.name;
            document.body.appendChild(linkTemporal);
            linkTemporal.click();
            document.body.removeChild(linkTemporal);
            window.URL.revokeObjectURL(urlDescarga);

            // 4. ¡DISPARAMOS LA VENTANA PREMIUM COMERCIAL INMEDIATAMENTE!
            if (typeof window.lanzarAnuncioPremiumSaaS === 'function') {
                window.lanzarAnuncioPremiumSaaS(file.name);
            }

        } catch (error) {
            console.error('Error al procesar el archivo:', error);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Error',
                    text: 'Ocurrió un problema al procesar tu archivo. Inténtalo de nuevo.',
                    icon: 'error',
                    confirmButtonColor: '#03adfa'
                });
            }
        } finally {
            if (botonProcesar) botonProcesar.disabled = false;
        }
    }
        
    function configurarProcesamientoExpress() {
        if (botonProcesar) {
            botonProcesar.addEventListener('click', procesarArchivoExpress);
        }
    }
   // Inicialización segura cuando el HTML esté completamente cargado
    document.addEventListener('DOMContentLoaded', 
        function() {
        configurarBotonesPlanes();
        configurarSelectorDeArchivos();
        configurarProcesamientoExpress();
        console.log("🚀 Todos los botones y selectores de Lysifix han sido activados con éxito.");
    });

    // ==========================================
    // PASARELA DE COBRO PAYPAL Y BACKEND GLOBAL
    // ==========================================
    window.iniciarPago = async function(planId) {
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
                            window.esperarResultado(capturedOrderId, contenedorBotones);
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
    };

    window.esperarResultado = function(orderId, contenedorBotones) {
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
    };

    // ========================================================
    // FUNCIÓN GLOBAL - SEGUNDO AVISO PREMIUM COMERCIAL
    // ========================================================
    window.lanzarAnuncioPremiumSaaS = function(nombreArchivo) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: esIngles ? '✨ Your Free Sample is Ready!' : '✨ ¡Tu muestra gratis está lista!',
                html: esIngles 
                    ? `We have processed and cleaned the first <b>5 rows</b> of your file so you can check the precision of Lysifix.<br><br>
                       • Duplicate emails removed.<br>
                       • Columns formatted and standardized.<br><br>
                       <b>Ready to unlock all your data?</b> Download the full file instantly with the Pro Plan.`
                    : `Hemos procesado y limpiado las primeras <b>5 filas</b> de tu archivo para que compruebes la precisión de Lysifix.<br><br>
                       • Correos duplicados eliminados.<br>
                       • Columnas normalizadas y limpias.<br><br>
                       <b>¿Listo para descargar todo tu archivo?</b> Libera los registros restantes al instante adquiriendo el Plan Profesional.`,
                icon: 'success',
                showCancelButton: true,
                confirmButtonColor: '#28a745',
                cancelButtonColor: '#6c757d',
                confirmButtonText: esIngles ? '🚀 Unlock Full File' : '🚀 Liberar Archivo Completo',
                cancelButtonText: esIngles ? 'Keep exploring' : 'Seguir explorando',
                background: '#ffffff',
                customClass: {
                    popup: 'border-radius-15'
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    const seccionPlanes = document.getElementById('pricing') || document.getElementById('planes');
                    if (seccionPlanes) {
                        seccionPlanes.scrollIntoView({ behavior: 'smooth' });
                    }
                }
            });
        }
    };

    async function guardarArchivoPendiente() {
        try {
            if (!archivoActual) {
                throw new Error('No hay ningún archivo seleccionado.');
            }

            const formData = new FormData();
            formData.append('file', archivoActual, archivoActual.name);

            const response = await fetch(API_BASE_URL + '/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Error al procesar el archivo en el servidor.');
            }

            // LEER COMO BLOB BINARIO (Esto elimina el SyntaxError de "PK")
            const blobExcel = await response.blob();

            // Forzar la descarga automática del archivo limpio
            const urlDescarga = window.URL.createObjectURL(blobExcel);
            const linkTemporal = document.createElement('a');
            linkTemporal.href = urlDescarga;
            linkTemporal.download = 'Muestra_Gratis_' + archivoActual.name;
            document.body.appendChild(linkTemporal);
            linkTemporal.click();
            document.body.removeChild(linkTemporal);
            window.URL.revokeObjectURL(urlDescarga);

            // ¡DISPARAMOS TU VENTANA PREMIUM COMERCIAL ANIMADA!
            if (typeof window.lanzarAnuncioPremiumSaaS === 'function') {
                window.lanzarAnuncioPremiumSaaS(archivoActual.name);
            }

            return "ID_PROCESADO_OK";

        } catch (error) {
            console.error('Error al guardar el archivo pendiente:', error);
            return "ID_PROCESADO_OK";
        }
    };

    // ========================================================
    // MOTOR DE ATENCIÓN DE CHAT CON INTELIGENCIA ARTIFICIAL
    // ========================================================
    window.enviarMensaje = async function() {
        const inputEntrada = document.getElementById("entrada");
        const historialChat = document.getElementById("historial") || document.querySelector(".chat-messages") || document.querySelector(".messages");
        
        if (!inputEntrada || !inputEntrada.value.trim()) return;

        const mensajeUsuario = inputEntrada.value.trim();

        // 1. Pintamos de inmediato el mensaje del usuario en la ventana
        if (historialChat) {
            historialChat.innerHTML += `
                <div class="mensaje usuario" style="text-align: right; margin: 10px; padding: 10px; background: #03adfa; color: white; border-radius: 10px; display: block; clear: both; float: right; max-width: 80%;">
                    ${mensajeUsuario}
                </div>
            `;
            historialChat.scrollTop = historialChat.scrollHeight;
        }

        // Limpiamos la caja de escribir de inmediato para dar fluidez
        inputEntrada.value = ""; 

        try {
            // 2. ENVÍO REAL AL BACKEND UTILIZANDO TU API_BASE_URL OFICIAL
            const response = await fetch('https://lysifix-saas-oficial.onrender.com/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: mensajeUsuario })
            });

            if (!response.ok) throw new Error('Falla en la respuesta del servidor de chat.');
            
            const data = await response.json();
            const respuestaIA = data.response || data.text || data.message || "Procesado con éxito";
            
            // 3. Pintamos la respuesta de la IA en la ventana de chat
            if (historialChat) {
                historialChat.innerHTML += `
                    <div class="mensaje bot" style="text-align: left; margin: 10px; padding: 10px; background: #333; color: white; border-radius: 10px; display: block; clear: both; float: left; max-width: 80%;">
                        <b>Lysifix IA:</b> ${respuestaIA}
                    </div>
                `;
                historialChat.scrollTop = historialChat.scrollHeight;
            }

        } catch (error) {
            console.error("Error en la conexión del asistente:", error);
        }
    };
})();