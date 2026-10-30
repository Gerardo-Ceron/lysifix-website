import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. RUTA PARA JALAR TU PORTAFOLIO VISUAL COMPLETO
@app.get("/", response_class=HTMLResponse)
async def home():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as archivo:
            return archivo.read()
    return "<h1>Lysifix: Servidor activo</h1>"

# 2. EL CONECTOR DEL CHAT (Mantiene tu bot inteligente)
class MensajeUsuario(BaseModel):
    message: str

def obtener_respuesta_ia(mensaje_usuario: str):
    mensaje = mensaje_usuario.lower()
    saludo_inicial = ""
    
    # 1. Almacenar el saludo si viene incluido en el mensaje
    if "hola" in mensaje or "buenos" in mensaje or "buenas" in mensaje or "buen" in mensaje:
        saludo_inicial = "Hola, ¿en qué puedo ayudarte? 😊\n\n"
        
    # 2. Evaluar intenciones de negocio prioritarias (Precios, Cotizaciones o Servicios Específicos)
    if any(palabra in mensaje for palabra in ["precio", "costo", "cuanto cuesta", "cotizacion", "cotización", "web", "automatiz", "dato", "archivo", "software", "script"]):
        return f"{saludo_inicial}Para conocer precios, automatizaciones y cotizaciones de páginas web, archivos o desarrollo de software, puedes visitar nuestro enlace oficial de Fiverr: https://fiverr.com..."
        
    elif "servicios" in mensaje or "que hacen" in mensaje or "desarrollo" in mensaje:
        return f"{saludo_inicial}En Lysifix nos especializamos en Desarrollo Web, automatización de datos y archivos, y Software a la medida. Creamos páginas web, aplicaciones y soluciones eficientes."
        
    elif "contacto" in mensaje or "telefono" in mensaje or "correo" in mensaje:
        return f"{saludo_inicial}Puedes dejarnos un mensaje en la sección de 'Contacto' de esta página."
        
    elif saludo_inicial != "":
        # Si el usuario solo dijo "hola" a secas, respondemos el saludo puro
        return saludo_inicial.strip()
        
    else:
        # Respuesta por defecto si no entiende nada de lo anterior
        return "Disculpa, todavía estoy aprendiendo y no entendí tu pregunta. ¿Podrías intentar preguntar de otra forma?"

@app.post("/chat")
async def chat_endpoint(datos: MensajeUsuario):
    if not datos.message or not datos.message.strip():
        return {"respuesta": "El mensaje no puede estar vacío"}
    respuesta_bot = obtener_respuesta_ia(datos.message)
    return {"respuesta": respuesta_bot}

# 3. TRUCO FINAL DE FASTAPI: Sirve todas tus carpetas (css, img, assets) de forma nativa
# Va hasta el final del archivo para que no tape las rutas del chat
app.mount("/", StaticFiles(directory=".", html=True), name="static")
