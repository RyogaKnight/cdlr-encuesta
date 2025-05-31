# ============================ IMPORTACIONES Y CONFIGURACIÓN INICIAL ============================

from flask import Flask, render_template, request, redirect, url_for, session
import os
import gspread
import psycopg2
from oauth2client.service_account import ServiceAccountCredentials
import json

# Inicializa la aplicación Flask
app = Flask(__name__)
app.secret_key = 'clave-super-secreta'  # Se usa para mantener la sesión segura entre páginas

# ============================ CONEXIÓN CON GOOGLE SHEETS ============================

# Define los permisos necesarios para acceder a Sheets y Drive
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Autenticación con Google mediante la variable de entorno GOOGLE_CREDS
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ============================ ENVIAR RESPUESTAS A SUPABASE ============================

def guardar_respuesta_en_supabase(cliente, area, pregunta, respuesta, encuesta_id=1):
    """
    Inserta cada respuesta en Supabase (PostgreSQL).
    Requiere la variable de entorno SUPABASE_URL con el string de conexión.
    """
    try:
        conn = psycopg2.connect(os.environ["SUPABASE_URL"])
        cursor = conn.cursor()

        # DEBUG: mostrar lo que se va a insertar
        print(f"Guardando respuesta -> Cliente: {cliente}, Área: {area}, Pregunta: {pregunta}, Respuesta: {respuesta}")

        cursor.execute("""
            INSERT INTO respuestas (encuesta, cliente, area, pregunta, respuesta)
            VALUES (%s, %s, %s, %s, %s)
        """, (encuesta_id, cliente, area, pregunta, respuesta))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("⚠️ Error al guardar en Supabase:", e)

# ============================ FUNCIONES AUXILIARES ============================

def cargar_clientes():
    """Carga la hoja 'Clientes' como diccionario para acceso rápido por nombre."""
    sheet = client.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    hoja_clientes = sheet.worksheet("Clientes")
    registros = hoja_clientes.get_all_records()
    return {fila['Cliente']: fila for fila in registros}

def cargar_preguntas_para_cliente(cliente, password):
    """
    Verifica si hay una encuesta activa y válida para el cliente.
    Extrae los IDs de preguntas asignadas y las organiza por área.
    """
    sheet = client.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    hoja_preguntas = sheet.worksheet("Preguntas")
    hoja_encuestas = sheet.worksheet("Encuestas")
    hoja_clientes = sheet.worksheet("Clientes")

    datos_preguntas = hoja_preguntas.get_all_records()
    datos_encuestas = hoja_encuestas.get_all_records()
    datos_clientes = hoja_clientes.get_all_records()

    encuesta = next((e for e in datos_encuestas if e["Activo"].strip().lower() == "yes" and e["Cliente"].strip() == cliente), None)
    if not encuesta:
        return None

    cliente_data = next((c for c in datos_clientes if c["Cliente"].strip() == cliente and c["Password"].strip() == password), None)
    if not cliente_data:
        return None

    ids_preguntas = [pid.strip() for pid in encuesta["Preguntas"].split(',')]

    preguntas_por_area = {}
    for pid in ids_preguntas:
        fila = next((p for p in datos_preguntas if str(p["ID"]).strip() == pid), None)
        if fila:
            area = fila["Area"].strip()
            preguntas_por_area.setdefault(area, []).append(fila["Pregunta"].strip())

    return preguntas_por_area

# Escala común para todas las respuestas
ESCALA = ["Nunca", "En ocasiones", "Con frecuencia", "Casi siempre", "Siempre"]

# ============================ RUTAS FLASK ============================

@app.route('/', methods=['GET', 'POST'])
def login():
    """Página de login para ingresar cliente y contraseña."""
    error = ""
    if request.method == 'POST':
        cliente_ingresado = request.form['cliente']
        password = request.form['password']

        preguntas_por_area = cargar_preguntas_para_cliente(cliente_ingresado, password)
        if preguntas_por_area:
            session['autenticado'] = True
            session['cliente'] = cliente_ingresado
            session['pagina'] = 0
            session['respuestas'] = {}
            session['preguntas'] = preguntas_por_area
            return redirect(url_for('formulario'))
        else:
            error = "Cliente, contraseña o configuración de encuesta incorrecta."

    return render_template("login.html", error=error)

@app.route('/encuesta', methods=['GET', 'POST'])
def formulario():
    """Página que muestra las preguntas una por una y guarda respuestas en sesión."""
    if not session.get('autenticado'):
        return redirect(url_for('login'))

    cliente = session['cliente']
    preguntas_por_area = session['preguntas']
    secciones = list(preguntas_por_area.keys())
    pagina = session.get('pagina', 0)

    if pagina >= len(secciones):
        return redirect(url_for('gracias'))

    area_actual = secciones[pagina]
    preguntas = preguntas_por_area[area_actual]
    cliente_info = CLIENTES.get(cliente, {"Logo": "", "Colorhex": "#FFFFFF"})

    if request.method == 'POST':
        respuestas_form = {}
        for i, pregunta in enumerate(preguntas):
            respuesta = request.form.get(f'{area_actual}_{i}')
            if not respuesta:
                error = "Por favor responde todas las preguntas antes de continuar."
                return render_template("encuesta.html", preguntas=preguntas, area=area_actual, escala=ESCALA,
                                       pagina=pagina, total=len(secciones), error=error,
                                       cliente_logo=cliente_info["Logo"], color_fondo=cliente_info["Colorhex"],
                                       cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")
            respuestas_form[f'{area_actual}_{i}'] = (area_actual, pregunta, respuesta)

        session['respuestas'].update(respuestas_form)

        if 'siguiente' in request.form:
            session['pagina'] += 1
        elif 'anterior' in request.form:
            session['pagina'] -= 1

        return redirect(url_for('formulario'))

    return render_template("encuesta.html", preguntas=preguntas, area=area_actual, escala=ESCALA,
                           pagina=pagina, total=len(secciones), error="",
                           cliente_logo=cliente_info["Logo"], color_fondo=cliente_info["Colorhex"],
                           cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")

@app.route('/gracias')
def gracias():
    """Página final. Guarda respuestas en Supabase y muestra agradecimiento."""
    cliente = session.get('cliente', '')
    cliente_info = CLIENTES.get(cliente, {"Logo": "", "Colorhex": "#FFFFFF"})

    for _, (area, pregunta, respuesta) in session['respuestas'].items():
        guardar_respuesta_en_supabase(cliente, area, pregunta, respuesta, encuesta_id=1)

    return render_template("gracias.html", cliente_logo=cliente_info["Logo"],
                           color_fondo=cliente_info["Colorhex"],
                           cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")

# ============================ INICIALIZADOR LOCAL ============================

if __name__ == '__main__':
    CLIENTES = cargar_clientes()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
