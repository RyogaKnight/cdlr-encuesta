
# ============================ IMPORTACIONES Y CONFIGURACIÓN INICIAL ============================

from flask import Flask, render_template, request, redirect, url_for, session
import os
import gspread
import psycopg2 
from oauth2client.service_account import ServiceAccountCredentials
import json

# Inicializa la aplicación Flask
app = Flask(__name__)
app.secret_key = 'clave-super-secreta'  # Se usa para firmar las sesiones y mantener datos seguros entre solicitudes

# ============================ CONEXIÓN CON GOOGLE SHEETS ============================

# Define los permisos necesarios para trabajar con Google Sheets y Google Drive
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Obtiene las credenciales del archivo JSON desde la variable de entorno GOOGLE_CREDS
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)  # Cliente autorizado para acceder a los datos del Google Sheet

# ============================ FUNCIONES AUXILIARES ============================

def cargar_clientes():
    """
    Carga todos los datos de la hoja 'Clientes' y los devuelve como un diccionario con el nombre del cliente como clave.
    Este diccionario se usa para buscar la contraseña, logo, colores y métodos de contacto del cliente.
    """
    sheet = client.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    hoja_clientes = sheet.worksheet("Clientes")
    registros = hoja_clientes.get_all_records()
    return {fila['Cliente']: fila for fila in registros}

def cargar_preguntas_para_cliente(cliente, password):
    """
    Obtiene los IDs de preguntas asignados en la hoja 'Encuestas' para el cliente indicado, 
    valida la contraseña contra la hoja 'Clientes', y extrae las preguntas correspondientes de la hoja 'Preguntas'.
    """
    sheet = client.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    hoja_preguntas = sheet.worksheet("Preguntas")
    hoja_encuestas = sheet.worksheet("Encuestas")
    hoja_clientes = sheet.worksheet("Clientes")

    datos_preguntas = hoja_preguntas.get_all_records()
    datos_encuestas = hoja_encuestas.get_all_records()
    datos_clientes = hoja_clientes.get_all_records()

    # Verifica si hay una encuesta activa para ese cliente
    encuesta = next((e for e in datos_encuestas if e["Activo"].strip().lower() == "yes" and e["Cliente"].strip() == cliente), None)
    if not encuesta:
        return None

    # Verifica la contraseña del cliente
    cliente_data = next((c for c in datos_clientes if c["Cliente"].strip() == cliente and c["Password"].strip() == password), None)
    if not cliente_data:
        return None

    # Extrae los IDs de las preguntas definidos en la hoja Encuesta
    ids_preguntas = [pid.strip() for pid in encuesta["Preguntas"].split(',')]

    # Agrupa las preguntas por área para dividirlas en secciones
    preguntas_por_area = {}
    for pid in ids_preguntas:
        fila = next((p for p in datos_preguntas if str(p["ID"]).strip() == pid), None)
        if fila:
            area = fila["Area"].strip()
            preguntas_por_area.setdefault(area, []).append(fila["Pregunta"].strip())

    return preguntas_por_area

# Escala fija usada para todas las encuestas
ESCALA = ["Nunca", "En ocasiones", "Con frecuencia", "Casi siempre", "Siempre"]

# ============================ RUTAS DE LA APLICACIÓN ============================

@app.route('/', methods=['GET', 'POST'])
def login():
    """
    Ruta principal: muestra un formulario para ingresar cliente y contraseña.
    Si son válidos, redirige al formulario de encuesta. En caso contrario, muestra mensaje de error.
    """
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
    """
    Muestra y gestiona las preguntas por secciones. Controla el avance (siguiente/anterior) 
    y guarda las respuestas en sesión. Al final, redirige a la página de agradecimiento.
    """
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

    # Obtiene información visual del cliente desde CLIENTES global
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
    """
    Página final después de completar la encuesta.
    Aquí también se guardan las respuestas en la base de datos PostgreSQL (Supabase).
    """
    cliente = session.get('cliente', '')
    cliente_info = CLIENTES.get(cliente, {"Logo": "", "Colorhex": "#FFFFFF"})

    # Guardar respuestas en Supabase
    for _, (area, pregunta, respuesta) in session['respuestas'].items():
        guardar_respuesta_en_supabase(cliente, area, pregunta, respuesta, encuesta_id=1)

    return render_template("gracias.html", cliente_logo=cliente_info["Logo"],
                           color_fondo=cliente_info["Colorhex"],
                           cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")

# ============================ ENVIAR RESPUESTAS A SUPABASE SQL ============================

def guardar_respuesta_en_supabase(cliente, area, pregunta, respuesta, encuesta_id=1):
    """
    Inserta una respuesta individual en la base de datos PostgreSQL de Supabase.
    Usa variables de entorno para seguridad.
    """
    try:
        conn = psycopg2.connect(os.environ["SUPABASE_URL"])
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO respuestas (encuesta, cliente, area, pregunta, respuesta)
            VALUES (%s, %s, %s, %s, %s)
        """, (encuesta_id, cliente, area, pregunta, respuesta))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error al guardar en Supabase:", e)


# ============================ INICIALIZADOR LOCAL ============================

if __name__ == '__main__':
    # Precarga los datos de clientes para visualización e imagen
    CLIENTES = cargar_clientes()

    # Render necesita que el host sea 0.0.0.0 y que el puerto se tome desde la variable de entorno "PORT"
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)