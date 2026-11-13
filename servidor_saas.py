import os
import pandas as pd
import io
import uuid
from flask import Flask, request, jsonify, send_from_directory, make_response, send_file
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from openai import OpenAI
from dotenv import load_dotenv

UPLOAD_FOLDER = "archivos_pendientes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 

load_dotenv()

# PRIMERO CREAMOS LA APP PARA QUE NO DE ERROR
app = Flask(__name__)

ALLOWED_ORIGINS = {
    "https://lysifix.dev",
    "https://www.lysifix.dev",
    "https://lysifix-website.onrender.com",
    "https://gerardo-ceron.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
}

CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})



# Configuración de OpenAI con credenciales automáticas
client = OpenAI()

# Configuración de Base de Datos SQLite local
engine = create_engine('sqlite:///lysifix.db', echo=True)
Base = declarative_base()
from sqlalchemy import Column, Integer, String

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    creditos = Column(Integer, default=100)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()
Base.metadata.create_all(bind=engine)
# ==========================================
# RUTAS PARA EL DISEÑO Y LA PÁGINA WEB
# ==========================================
@app.route('/')
@app.route('/index.html')
def home():
    from flask import send_from_directory
    return send_from_directory('.', 'index.html')

@app.route('/estilos.css')
def css():
    from flask import send_from_directory
    return send_from_directory('.', 'estilos.css')

@app.route('/favicon-32x32.png')
def favicon32():
    from flask import send_from_directory
    return send_from_directory('.', 'favicon-32x32.png')

@app.route('/favicon-16x16.png')
def favicon16():
    from flask import send_from_directory
    return send_from_directory('.', 'favicon-16x16.png')

# ==========================================
# RUTAS PARA LA VERSIÓN EN INGLÉS
# ==========================================
@app.route('/en')
@app.route('/en/index.html')
def home_en():
    from flask import send_from_directory
    import os
    ruta_ingles = os.path.join('.', 'en')
    return send_from_directory(ruta_ingles, 'index.html')

@app.route('/en/<path:filename>')
def archivos_en(filename):
    from flask import send_from_directory
    import os
    ruta_ingles = os.path.join('.', 'en')
    return send_from_directory(ruta_ingles, filename)

# ==========================================
# RUTA PARA CONSUMIR CRÉDITOS Y LLAMAR A OPENAI
# ==========================================
@app.route('/api/consumir_credito', methods=['POST', 'OPTIONS'])
def consumir_credito():
    # Manejo automático de peticiones de seguridad del navegador (Preflight)
    import flask
    if flask.request.method == 'OPTIONS':
        voto = flask.make_response()
        voto.headers.add("Access-Control-Allow-Origin", "*")
        voto.headers.add('Access-Control-Allow-Headers', "*")
        voto.headers.add('Access-Control-Allow-Methods', "*")
        return voto

    datos = request.get_json() or {}
    email_usuario = datos.get('email', 'anonimo')
    mensaje_usuario = datos.get('mensaje', '')

    if not mensaje_usuario:
        respuesta = jsonify({"status": "error", "message": "El mensaje está vacío"})
        respuesta.headers.add("Access-Control-Allow-Origin", "*")
        return respuesta, 400
        
    usuario = session.query(Usuario).filter_by(email=email_usuario).first()
    if not usuario:
        usuario = Usuario(email=email_usuario, creditos=100)
        session.add(usuario)
        session.commit()
        
    if usuario.creditos <= 0:
        return jsonify({"status": "bloqueado", "message": "Créditos agotados. Redirigiendo al Paywall."}), 403

    try:
        instrucciones = (
    "Eres el asistente virtual oficial de Lysifix. "
    "Lysifix fue diseñado y desarrollado por Gerardo Cerón, especialista en automatización y desarrollo de software. "
    "Responde de forma breve, clara y profesional. "
    "Lysifix ofrece una prueba gratuita donde el usuario puede subir un archivo y recibir una muestra procesada automáticamente. "
    "Además, cuenta con servicios automáticos en la plataforma con los siguientes planes: "
    "Plan Básico: $35 USD, Plan Profesional: $45 USD, "
    "Plan Avanzado: $75 USD y Plan Premium: $150 USD. "
    "Para trabajos rápidos y estándar, los usuarios pueden subir sus archivos y procesarlos automáticamente. "
    "Si el usuario busca software personalizado, automatizaciones avanzadas, web scraping complejo o una solución totalmente a medida, "
     "indícale que puede contratar los servicios profesionales de Lysifix en Fiverr y escribe exactamente [BOTON_FIVERR] al final de tu respuesta. "
    "Procura responder en pocas líneas, evitando explicaciones innecesariamente largas. "
    "Responde siempre en el mismo idioma en el que escriba el usuario."
        )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instrucciones},
                {"role": "user", "content": mensaje_usuario}
            ]
        )
        respuesta_ia = completion.choices[0].message.content
        usuario.creditos -= 1
        session.commit()
        return jsonify({"status": "success", "creditos_restantes": usuario.creditos, "respuesta": respuesta_ia})
    except Exception as e:
        session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

# from flask import Flask, request, jsonify, make_response, send_from_directory

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
   
    try:
        datos = request.get_json()
        mensaje_usuario = datos.get('mensaje')
        
        # 1. LEEMOS EL IDIOMA QUE MANDA TU PÁGINA (Si no viene, por defecto es español)
        idioma_pagina = datos.get('idioma', 'en')

        # 2. SELECCIONAMOS LAS INSTRUCCIONES SEGÚN EL IDIOMA
        if idioma_pagina == 'en':
            instrucciones = (
                "You are the official virtual assistant of Lysifix. "
                "Lysifix was designed and developed by Gerardo Cerón, a specialist in automation and software development. "
                "Reply in a brief, clear, and professional manner. "
                "Lysifix offers a free trial where users can upload a file and receive a processed sample automatically. "
                "Lysifix also provides automated services on the platform with the following plans: "
                "Basic Plan: $35 USD, Professional Plan: $45 USD, "
                "Advanced Plan: $75 USD, and Premium Plan: $150 USD. "
                "For quick and standard tasks, users can upload files and have them processed automatically. "
                "If the user is looking for custom software, advanced automation, complex web scraping, or a fully personalized solution, "
                "inform them that professional services can be hired through Fiverr and write the exact tag [BOTON_FIVERR] at the end of your reply. "
                "Keep responses short and easy to understand. "
                "Always reply in the same language used by the user."
            )
        else:
            instrucciones = (
                "Eres el asistente virtual oficial de Lysifix. "
                "Lysifix fue diseñado y desarrollado por Gerardo Cerón, especialista en automatización y desarrollo de software. "
                "Responde de forma breve, clara y profesional. "
                "Lysifix ofrece una prueba gratuita donde el usuario puede subir un archivo y recibir una muestra procesada automáticamente. "
                "Además, cuenta con servicios automáticos en la plataforma con los siguientes planes: "
                "Plan Básico: $35 USD, Plan Profesional: $45 USD, "
                "Plan Avanzado: $75 USD y Plan Premium: $150 USD. "
                "Para trabajos rápidos y estándar, los usuarios pueden subir sus archivos y procesarlos automáticamente. "
                "Si el usuario busca software personalizado, automatizaciones avanzadas, web scraping complejo o una solución totalmente a medida, "
                "indícale que puede contratar los servicios profesionales de Lysifix en Fiverr y escribe exactamente [BOTON_FIVERR] al final de tu respuesta. "
                "Procura responder en pocas líneas, evitando explicaciones innecesariamente largas. "
                "Responde siempre en el mismo idioma en el que escriba el usuario."
            )


        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instrucciones},
                {"role": "user", "content": mensaje_usuario}
            ]
        )

        respuesta_ia = completion.choices[0].message.content
        mostrar_fiverr = False

        # Detectamos si la IA incluyó la etiqueta y la limpiamos del texto visible
        if "[BOTON_FIVERR]" in respuesta_ia:
            mostrar_fiverr = True
            respuesta_ia = respuesta_ia.replace("[BOTON_FIVERR]", "").strip()

        return jsonify({
            "respuesta": respuesta_ia,
            "mostrar_fiverr": mostrar_fiverr,
            "url_fiverr": "https://es.fiverr.com/gerardo_cg"
        })


    except Exception as e:
       return jsonify({"status": "error", "message": str(e)})

@app.route('/upload', methods=['POST', 'OPTIONS'])
def procesar_archivo_express():
    if not request.files:
        return jsonify({"error": "No se recibió ningún archivo"})

    archivo = next(iter(request.files.values()))
    nombre = archivo.filename or ""
    extension = os.path.splitext(nombre)[1].lower()

    try:
        print("ENTRO AL TRY")

        if extension == ".csv":
            dataframe = pd.read_csv(archivo)
            mimetype = "text/csv"
        else:
            dataframe = pd.read_excel(archivo, engine="openpyxl")
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        if len(dataframe) > 10000:
            return jsonify({
                "error": "Archivo demasiado grande para el servicio express"
            }), 400

        dataframe.drop_duplicates(inplace=True)
        dataframe.columns = dataframe.columns.astype(str).str.strip().str.upper()
        dataframe.dropna(how="all", axis=1, inplace=True)

        # Muestra gratuita de 5 filas
        dataframe = dataframe.head(5)


        output = io.BytesIO()
        if extension == ".csv":
            dataframe.to_csv(output, index=False)
        else:
            dataframe.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)

        response = send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"Lysifix_Express_{os.path.basename(nombre)}"
        )
        return response
    except (ValueError, ImportError) as error:
        return jsonify({
            "error": f"No se pudo procesar el archivo: {error}"
        }), 400
    except Exception:
        app.logger.exception("Error procesando archivo")
        return jsonify({
            "error": "El archivo requiere análisis personalizado"
        }), 500

@app.route('/api/archivos-pendientes', methods=['GET', 'POST'])
def guardar_archivo_pendiente():

    if request.method == 'GET':
        return jsonify({
            "status": "ok",
            "message": "Ruta encontrada"
        })

    if not request.files:
        return jsonify({
            "status": "error",
            "message": "No se recibió archivo"
        }), 400

    archivo = next(iter(request.files.values()))

    extension = os.path.splitext(archivo.filename)[1]

    file_id = f"{uuid.uuid4()}{extension}"

    ruta_archivo = os.path.join(
        UPLOAD_FOLDER,
        file_id
    )

    archivo.save(ruta_archivo)

    return jsonify({
        "status": "success",
        "file_id": file_id
    })

    # ==========================================
# VERIFICAR PAGO Y PROCESAR
# ==========================================

trabajos = {}

@app.route('/api/verificar_pago_y_procesar', methods=['POST'])
def verificar_pago_y_procesar():

    datos = request.get_json()

    order_id = datos.get('order_id')
    plan = datos.get('plan')
    email = datos.get('email')
    file_id = datos.get('file_id')

    print("Pago recibido:")
    print(order_id)
    print(plan)
    print(email)
    print(file_id)

    trabajos[order_id] = {
        "status": "listo",
        "archivo_salida": file_id
    }

    return jsonify({
        "status": "success",
        "message": "Pago registrado correctamente"
    })


# ==========================================
# CONSULTAR ESTADO DEL TRABAJO
# ==========================================

@app.route('/api/estado_trabajo/<order_id>')
def estado_trabajo(order_id):

    trabajo = trabajos.get(order_id)

    if not trabajo:
        return jsonify({
            "status": "procesando"
        })

    return jsonify(trabajo)


# ==========================================
# DESCARGAR ARCHIVO
# ==========================================

@app.route('/api/descargar/<nombre_archivo>')
def descargar_archivo(nombre_archivo):

    return jsonify({
        "status": "success",
        "message": f"Archivo listo: {nombre_archivo}"
    })

if __name__ == '__main__':
     port = int(os.environ.get("PORT", 5000))
     app.run(host='0.0.0.0', port=port)
    
    