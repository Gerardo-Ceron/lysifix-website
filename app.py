import io
import os
import threading
import uuid
from pathlib import Path
import time
import requests
from flask import Flask, request, jsonify, send_from_directory
import httpx
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel
from werkzeug.utils import secure_filename

load_dotenv()


# ==========================================
# CONFIGURACION
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DOWNLOAD_DIR = BASE_DIR / "downloads"
UPLOAD_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
PLAN_CREDITS = {
    "precio_basico_id": 100,
    "precio_profesional_id": 250,
    "precio_avanzado_id": 500,
    "precio_premium_id": 1500,
}
PLAN_PRICES = {
    "precio_basico_id": "35.00",
    "precio_profesional_id": "45.00",
    "precio_avanzado_id": "75.00",
    "precio_premium_id": "150.00",
}
PAYPAL_API_BASE_URL = os.environ.get(
    "PAYPAL_API_BASE_URL",
    "https://api-m.sandbox.paypal.com",
).rstrip("/")
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
MAX_FILE_SIZE = 25 * 1024 * 1024

app = FastAPI(title="Lysifix API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado temporal de trabajos. Para producción con varias instancias debe migrarse
# a una cola y almacenamiento persistente.
TRABAJOS_ACTIVOS = {}
USUARIOS = {}
ARCHIVOS_PENDIENTES = {}
ORDENES_PROCESADAS = set()


# ==========================================
# PAGINAS Y CHAT
# ==========================================
@app.post("/")
async def procesar_chat(request: Request):
    datos = await request.json()
    # Aquí iría tu lógica vieja que procesa el mensaje del usuario
    index_path = BASE_DIR / "index.html"
    if not index_path.exists():
        return "<h1>Lysifix: Servidor activo</h1>"
    return index_path.read_text(encoding="utf-8")


@app.get("/en", response_class=HTMLResponse)
@app.get("/en/", response_class=HTMLResponse)
async def home_en():
    index_path = BASE_DIR / "en" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Página en inglés no encontrada.")
    return index_path.read_text(encoding="utf-8")


class MensajeUsuario(BaseModel):
    message: str | None = None
    mensaje: str | None = None


def obtener_respuesta_ia(mensaje_usuario: str) -> str:
    mensaje = mensaje_usuario.lower()
    saludo = ""

    if any(palabra in mensaje for palabra in ("hola", "buenos", "buenas", "buen")):
        saludo = "Hola, ¿en qué puedo ayudarte? 😊\n\n"

    if any(palabra in mensaje for palabra in (
        "precio", "costo", "cuanto cuesta", "cotizacion", "cotización",
        "web", "automatiz", "dato", "archivo", "software", "script"
    )):
        return (
            f"{saludo}Para conocer precios, automatizaciones y cotizaciones "
            "puedes visitar nuestro enlace oficial de Fiverr: https://fiverr.com..."
        )
    if any(palabra in mensaje for palabra in ("servicios", "que hacen", "desarrollo")):
        return (
            f"{saludo}En Lysifix nos especializamos en desarrollo web, "
            "automatización de datos y software a la medida."
        )
    if any(palabra in mensaje for palabra in ("contacto", "telefono", "correo")):
        return f"{saludo}Puedes dejarnos un mensaje en la sección de contacto."
    if saludo:
        return saludo.strip()
    return "Disculpa, todavía estoy aprendiendo y no entendí tu pregunta."



# ==========================================
# PROCESAMIENTO EXPRESS
# ==========================================
def obtener_extension(filename: str) -> str:
    return filename.lower().rsplit(".", 1)[-1] if "." in filename else ""


async def leer_dataframe(file: UploadFile, extension: str) -> pd.DataFrame:
    contenido = await file.read()
    if extension == "csv":
        return pd.read_csv(io.BytesIO(contenido))
    engine = "xlrd" if extension == "xls" else "openpyxl"
    return pd.read_excel(io.BytesIO(contenido), engine=engine)


def convertir_dataframe(df: pd.DataFrame, extension: str) -> tuple[bytes, str]:
    output = io.BytesIO()
    if extension == "csv":
        df.to_csv(output, index=False)
        media_type = "text/csv"
    else:
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return output.getvalue(), media_type


@app.post("/api/archivos-pendientes")
async def guardar_archivo_pendiente(file: UploadFile = File(...)):
    filename = (file.filename or "").strip()
    extension = obtener_extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato no soportado.")

    contenido = await file.read()
    if len(contenido) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo no puede superar los 25 MB.")

    nombre_seguro = secure_filename(filename)
    if not nombre_seguro:
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido.")

    file_id = uuid.uuid4().hex
    ruta_archivo = UPLOAD_DIR / f"{file_id}_{nombre_seguro}"
    ruta_archivo.write_bytes(contenido)
    ARCHIVOS_PENDIENTES[file_id] = {
        "path": ruta_archivo,
        "filename": nombre_seguro,
    }
    return {"status": "success", "file_id": file_id, "filename": nombre_seguro}


@app.post("/procesar-archivo")
@app.post("/upload")
async def procesar_archivo(file: UploadFile = File(...)):
    filename = (file.filename or "").strip()
    extension = obtener_extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato no soportado.")

    try:
        dataframe = await leer_dataframe(file, extension)
        columna_email = next(
            (col for col in dataframe.columns if "email" in str(col).lower()),
            None,
        )
        if columna_email:
            dataframe = dataframe.drop_duplicates(subset=[columna_email])

        contenido, media_type = convertir_dataframe(dataframe, extension)
        nombre_seguro = secure_filename(filename) or f"archivo.{extension}"
        return Response(
            content=contenido,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="limpio_{nombre_seguro}"'},
        )
    except (ValueError, ImportError) as error:
        raise HTTPException(status_code=400, detail=f"No se pudo procesar el archivo: {error}") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Error interno al procesar el archivo.") from error


# ==========================================
# PROCESAMIENTO POSTERIOR AL PAGO
# ==========================================
def procesar_archivo_automatico(usuario_email: str, ruta_entrada: Path, order_id: str):
    try:
        TRABAJOS_ACTIVOS[order_id] = {"status": "procesando", "archivo_salida": None}
        if not ruta_entrada.exists():
            raise FileNotFoundError("No se encontró el archivo seleccionado.")

        extension = obtener_extension(ruta_entrada.name)
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError("Formato de archivo no soportado.")

        if extension == "csv":
            dataframe = pd.read_csv(ruta_entrada)
        else:
            engine = "xlrd" if extension == "xls" else "openpyxl"
            dataframe = pd.read_excel(ruta_entrada, engine=engine)

        columna_email = next(
            (col for col in dataframe.columns if "email" in str(col).lower()),
            None,
        )
        if columna_email:
            dataframe = dataframe.drop_duplicates(subset=[columna_email])

        nombre_salida = f"resultado_{order_id}.{extension}"
        ruta_salida = DOWNLOAD_DIR / nombre_salida
        contenido, _ = convertir_dataframe(dataframe, extension)
        ruta_salida.write_bytes(contenido)

        TRABAJOS_ACTIVOS[order_id] = {
            "status": "listo",
            "archivo_salida": nombre_salida,
        }
        print(f"Trabajo terminado para {usuario_email}: {nombre_salida}")
    except Exception as error:
        TRABAJOS_ACTIVOS[order_id] = {"status": "error", "message": str(error)}
        print(f"Error procesando {order_id}: {error}")


class SolicitudPago(BaseModel):
    email: str = "anonimo"
    plan: str
    order_id: str
    file_id: str


async def obtener_token_paypal() -> str:
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="El servidor no tiene configuradas las credenciales de PayPal.",
        )

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{PAYPAL_API_BASE_URL}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
        )
    if response.status_code != 200:
        print(f"PayPal token error: {response.status_code} {response.text[:500]}")
        raise HTTPException(status_code=502, detail="No se pudo validar PayPal.")
    return response.json()["access_token"]


async def verificar_orden_paypal(order_id: str, plan_id: str):
    token = await obtener_token_paypal()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
    if response.status_code != 200:
        print(f"PayPal order error: {response.status_code} {response.text[:500]}")
        raise HTTPException(status_code=402, detail="No se pudo verificar la orden de PayPal.")

    order = response.json()
    purchase_units = order.get("purchase_units", [])
    amount = purchase_units[0].get("amount", {}) if purchase_units else {}
    if (
        order.get("status") != "COMPLETED"
        or amount.get("currency_code") != "USD"
        or amount.get("value") != PLAN_PRICES[plan_id]
    ):
        raise HTTPException(status_code=402, detail="La orden de PayPal no coincide con el plan.")
    return order


@app.post("/api/verificar_pago_y_procesar")
async def verificar_pago_y_procesar(datos: SolicitudPago):
    if datos.plan not in PLAN_CREDITS:
        raise HTTPException(status_code=400, detail="Plan no válido.")
    if datos.order_id in ORDENES_PROCESADAS:
        raise HTTPException(status_code=409, detail="Esta orden ya fue procesada.")
    archivo = ARCHIVOS_PENDIENTES.get(datos.file_id)
    if not archivo or not archivo["path"].is_file():
        raise HTTPException(status_code=404, detail="No se encontró el archivo pendiente.")

    await verificar_orden_paypal(datos.order_id, datos.plan)
    ORDENES_PROCESADAS.add(datos.order_id)

    usuario = USUARIOS.setdefault(datos.email, {"creditos": 0})
    usuario["creditos"] += PLAN_CREDITS[datos.plan]

    ruta_entrada = archivo["path"]
    threading.Thread(
        target=procesar_archivo_automatico,
        args=(datos.email, ruta_entrada, datos.order_id),
        daemon=True,
    ).start()
    del ARCHIVOS_PENDIENTES[datos.file_id]

    return {
        "status": "success",
        "message": "Pago registrado y procesamiento iniciado.",
        "order_id": datos.order_id,
        "creditos_totales": usuario["creditos"],
    }


@app.get("/api/estado_trabajo/{order_id}")
async def estado_trabajo(order_id: str):
    return TRABAJOS_ACTIVOS.get(order_id, {"status": "no_encontrado"})


@app.get("/api/descargar/{nombre_archivo}")
async def descargar_archivo(nombre_archivo: str):
    nombre_seguro = secure_filename(nombre_archivo)
    ruta_archivo = DOWNLOAD_DIR / nombre_seguro
    if not nombre_seguro or not ruta_archivo.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return FileResponse(ruta_archivo, filename=nombre_seguro)

# Inicialización de directorios seguros para el procesamiento autónomo
CARPA_SUBIDAS = './uploads'
CARPA_DESCARGAS = './downloads'
os.makedirs(CARPA_SUBIDAS, exist_ok=True)
os.makedirs(CARPA_DESCARGAS, exist_ok=True)

# Monitoreo en memoria del estado de procesamiento de los archivos por orden
TRABAJOS_ACTIVOS = {}

# Carga de credenciales desde el entorno
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_API_BASE_URL = os.getenv("PAYPAL_API_BASE_URL", "https://api-m.paypal.com")

def procesar_archivo_automatico(usuario_email, ruta_entrada, order_id):
    """
    Motor asíncrono en segundo plano: aquí corre el procesamiento de tus archivos.
    """
    try:
        TRABAJOS_ACTIVOS[order_id] = {"status": "procesando", "archivo_salida": None}
        print(f"🤖 [AUTOMATIZACIÓN] Procesando archivo de {usuario_email}...")

        # -----------------------------------------------------------------
        # ZONA DE TU SCRIPT PERSONALIZADO (Ejemplo de procesamiento automatizado)
        # -----------------------------------------------------------------
        time.sleep(8)  # Simula el lapso en el que tu programa ejecuta su magia
        
        nombre_salida = f"resultado_{order_id}.xlsx"
        ruta_salida = os.path.join(CARPA_DESCARGAS, nombre_salida)
        
        # Generación simulada del entregable final para el cliente
        with open(ruta_salida, "w") as f:
            f.write("Archivo estructurado procesado automáticamente por el motor SaaS de Lysifix.")
        # -----------------------------------------------------------------

        # Al terminar con éxito, marcamos como listo el estado para habilitar la descarga
        TRABAJOS_ACTIVOS[order_id] = {"status": "listo", "archivo_salida": nombre_salida}
        print(f"✅ [AUTOMATIZACIÓN] ¡Archivo listo para descargar! Orden: {order_id}")

    except Exception as e:
        TRABAJOS_ACTIVOS[order_id] = {"status": "error", "message": str(e)}
        print(f"❌ [ERROR AUTOMATIZACIÓN] Falló el script para {usuario_email}: {str(e)}")


@app.post('/api/verificar_pago_y_procesar')
def verificar_pago_y_procesar():
    datos = request.get_json() or {}
    email_usuario = datos.get('email', 'anonimo')
    plan_id = datos.get('plan')
    order_id = datos.get('order_id')
    nombre_archivo = datos.get('nombre_archivo')

    if not order_id or not plan_id:
        return jsonify({"status": "error", "message": "Datos de pago o identificador de orden ausentes"}), 400

    ruta_entrada = os.path.join(CARPA_SUBIDAS, secure_filename(nombre_archivo)) if nombre_archivo else None

    # Diccionario blindado de asignación de créditos
    CREDITOS_POR_PLAN = {
        'precio_basico_id': 100,
        'precio_profesional_id': 250,
        'precio_avanzado_id': 500,
        'precio_premium_id': 1500
    }
    creditos_a_sumar = CREDITOS_POR_PLAN.get(plan_id, 0)

    try:
        # Validación opcional: Verificar el estatus del ID de orden contra la API de PayPal si es requerido
        # response = requests.get(f"{PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}", ...)
        
        # Búsqueda o registro de la cuenta del cliente para la adición de créditos
        usuario = db_session.query(Usuario).filter_by(email=email_usuario).first()
        if not usuario:
            usuario = Usuario(email=email_usuario, creditos=100)
            db_session.add(usuario)
        
        usuario.creditos += creditos_a_sumar
        db_session.commit()
        print(f"💰 [PAYMENT] Transacción {order_id} aprobada para {email_usuario}. Créditos actualizados.")

        # Disparo inmediato del script en un hilo secundario para mantener veloz la experiencia web
        hilo = threading.Thread(target=procesar_archivo_automatico, args=(email_usuario, ruta_entrada, order_id))
        hilo.start()

        return jsonify({"status": "success", "message": "Pago registrado. Iniciando procesamiento.", "order_id": order_id})
    except Exception as e:
        db_session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.get('/api/estado_trabajo/{order_id}')
def constatar_estado_trabajo(order_id):
    """Ruta de monitoreo constante (polling) para verificar el estatus del archivo"""
    estado = TRABAJOS_ACTIVOS.get(order_id, {"status": "no_encontrado"})
    return jsonify(estado)


@app.get('/api/descargar/{nombre_archivo}')
def descargar_archivo(nombre_archivo):
    """Ruta segura de despacho que descarga el archivo resultante en el equipo del cliente"""
    return send_from_directory(CARPA_DESCARGAS, secure_filename(nombre_archivo), as_attachment=True)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        reload=False,
    )

# === CONEXIÓN CON OPENAI ===
@app.post("/chat")
async def procesar_chat(datos: MensajeUsuario):
    try:
        # FastAPI automáticamente procesa el JSON por ti usando 'datos'
        mensaje_usuario = datos.mensaje.strip() if datos.mensaje else ""
        
        if not mensaje_usuario:
            return {"respuesta": "El mensaje no puede estar vacío."}
            
        # === AQUÍ COMIENZA TU BLOQUE DE OPENAI ===
        from openai import OpenAI
        client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres el asistente oficial de Lysifix."},
                {"role": "user", "content": mensaje_usuario}
            ]
        )
        return {"respuesta": response.choices[0].message.content}
        
    except Exception as e:
        print(f"Error: {e}")
        return {"respuesta": "Hubo un error técnico."}
    try:
        from openai import OpenAI
        # Inicializa el cliente. Asegúrate de tener tu clave configurada
        # en las variables de entorno o ponla entre comillas aquí: client = OpenAI(api_key="TU_API_KEY")
        client = OpenAI() 
        
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Es el modelo más rápido y económico actual
            messages=[
                {"role": "system", "content": "Eres el asistente oficial de Lysifix. Sé amable, profesional y ayuda a los usuarios con sus dudas sobre desarrollo y automatización."},
                {"role": "user", "content": mensaje_usuario}
            ]
        )
        # Retornamos la respuesta real de la Inteligencia Artificial
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error detectado en OpenAI: {e}")
        # Si la API falla (por falta de saldo o API Key), dejamos este mensaje como plan de respaldo
        return "Disculpa, en este momento tengo un problema técnico para conectarme con mi cerebro de IA. Por favor, intenta de nuevo en unos minutos."