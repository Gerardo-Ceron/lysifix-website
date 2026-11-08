import os
import pandas as pd
import io
from flask import Flask, request, jsonify, send_from_directory, make_response, send_file
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from openai import OpenAI
from dotenv import load_dotenv

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
        instrucciones = "Eres el asistente virtual oficial de Lysifix, una plataforma que ofrece soluciones de automatización y servicios SaaS. Tu objetivo es guiar al usuario según el tamaño de su proyecto. Si el usuario busca algo rápido o automático, menciónale que Lysifix cuenta con servicios automáticos directamente en la página con tres planes: Básico de $5 dólares, Medio de $20 dólares y Pro de $50 dólares; explícale que si su servicio es pequeño o de urgencia, puede subir sus archivos en la plataforma y el programa se los trabajará en minutos de forma 100% automática. Por otro lado, aclara que si lo que busca es un programa mucho más específico, personalizado o con instrucciones más locochonas, puede solicitar el servicio a través de Fiverr, donde Lysifix trabaja y entrega los proyectos de forma totalmente segura. Sé muy carismático, profesional, habla siempre en tercera persona en nombre de la marca y responde SIEMPRE en el mismo idioma en el que el usuario te escriba."

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
                "You are the official virtual assistant for Lysifix, a platform that offers automation solutions and SaaS services. "
                "Your goal is to guide the user based on their project size. If the user asks for pricing, quotes, or if you can do web scraping (data extraction), "
                "immediately mention that Lysifix offers automated services directly on the website with three plans: Basic for $5 USD, Medium for $20 USD, and Pro for $50 USD. "
                "Explain that if their request is small or urgent, they can upload their files to the platform and the program will process them in minutes, 100% automatically. "
                "On the other hand, clarify that if they are looking for a much more specific, custom software or with crazier/complex instructions, they can request the service through Fiverr, where Lysifix works and delivers projects completely securely. "
                "Be very charismatic, professional, always speak in the third person on behalf of the brand, and ALWAYS reply in the same language the user is writing to you."
            )
        else:
            instrucciones = (
                "Eres el asistente virtual oficial de Lysifix, una plataforma que ofrece soluciones de automatización y servicios SaaS. "
                "Tu objetivo es guiar al usuario según el tamaño de su proyecto. Si el usuario te pregunta por precios, cotizaciones o si puedes hacer un web scraping (extracción de datos), "
                "menciónale de inmediato que Lysifix cuenta con servicios automáticos directamente en la página con tres planes: Básico de $5 dólares, Medio de $20 dólares y Pro de $50 dólares; "
                "explícle que si su servicio es pequeño o de urgencia, puede subir sus archivos en la plataforma y el programa se los trabajará en minutos de forma 100% automática. "
                "Por otro lado, aclara que si lo que busca es un programa o web scraper mucho más específico, personalizado o con instrucciones más locochonas, puede solicitar el servicio a través de Fiverr, "
                "donde Lysifix trabaja y entrega los proyectos de forma totalmente segura. "
                "Sé muy carismático, profesional, habla siempre en tercera persona en nombre de la marca y responde SIEMPRE en el mismo idioma en el que el usuario te escriba."
            )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instrucciones},
                {"role": "user", "content": mensaje_usuario}
            ]
        )

        respuesta_ia = completion.choices[0].message.content

        return jsonify({"status": "success", "respuesta": respuesta_ia})

    except Exception as e:
       return jsonify({"status": "error", "message": str(e)})

@app.route('/upload', methods=['POST', 'OPTIONS'])
def procesar_archivo_express():
    if not request.files:
        return jsonify({"error": "No se recibió ningún archivo"})
        
    archivo = next(iter(request.files.values()))
    nombre = archivo.filename or ""
    extension = os.path.splitext(nombre)[1].lower()

    if extension not in {".csv", ".xlsx", ".xls"}:
        return jsonify({"error": "Formato no compatible"})

    try:
        if extension == ".csv":
            dataframe = pd.read_csv(archivo)
            mimetype = "text/csv"
        else:
            dataframe = pd.read_excel(archivo, engine="openpyxl")
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        if len(dataframe) > 10000:
            return add_cors_headers(jsonify({"error": "Archivo demasiado grande para el servicio express"})), 400

        dataframe.drop_duplicates(inplace=True)
        dataframe.columns = dataframe.columns.astype(str).str.strip().str.upper()
        dataframe.dropna(how="all", axis=1, inplace=True)

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
            download_name=f"Lysifix_Express_{os.path.basename(nombre)}",
        )
        return add_cors_headers(response)
    except (ValueError, ImportError) as error:
        return add_cors_headers(jsonify({"error": f"No se pudo procesar el archivo: {error}"})), 400
    except Exception:
        app.logger.exception("Error procesando archivo")
        return add_cors_headers(jsonify({"error": "El archivo requiere análisis personalizado"})), 500

if __name__ == '__main__':
     port = int(os.environ.get("PORT", 5000))
     app.run(host='0.0.0.0', port=port)
    