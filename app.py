from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============================
# Sección: Inicialización de Flask
# ============================
app = Flask(__name__)
app.secret_key = 'clave-super-secreta'  # Necesaria para usar sesiones

# ============================
# Sección: Google Sheets - Autenticación y lectura
# ============================
import json
from io import StringIO

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ============================
# Sección: Lectura dinámica desde Google Sheets
# ============================
def cargar_preguntas():
    sheet = client.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    hoja = sheet.worksheet("Preguntas")
    data = hoja.get_all_records()
    preguntas = {}
    for row in data:
        if row['Activo'].strip().lower() == 'si':
            area = row['Area'].strip()
            preguntas.setdefault(area, []).append(row['Pregunta'].strip())
    return preguntas

def cargar_clientes():
    sheet = client.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    hoja = sheet.worksheet("Clientes")
    clientes = hoja.get_all_records()
    return {cliente['Cliente']: cliente for cliente in clientes}

PREGUNTAS = cargar_preguntas()
CLIENTES = cargar_clientes()
SECCIONES = list(PREGUNTAS.keys())
ESCALA = ["Nunca", "En ocasiones", "Con frecuencia", "Casi siempre", "Siempre"]

# ============================
# Sección: Inicialización de base de datos
# ============================
def init_db():
    conn = sqlite3.connect('respuestas.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS respuestas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 cliente TEXT,
                 area TEXT,
                 pregunta TEXT,
                 respuesta TEXT
                 )''')
    conn.commit()
    conn.close()

# ============================
# Sección: Ruta de login
# ============================
@app.route('/', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        cliente_ingresado = request.form['cliente']
        password = request.form['password']
        cliente_data = CLIENTES.get(cliente_ingresado)
        if cliente_data and password == cliente_data['password']:
            session['autenticado'] = True
            session['cliente'] = cliente_ingresado
            session['pagina'] = 0
            session['respuestas'] = {}
            return redirect(url_for('formulario'))
        else:
            error = "Cliente o contraseña incorrectos."
    return render_template("login.html", error=error)

# ============================
# Sección: Formulario dividido por secciones
# ============================
@app.route('/encuesta', methods=['GET', 'POST'])
def formulario():
    if not session.get('autenticado'):
        return redirect(url_for('login'))

    pagina = session.get('pagina', 0)
    area_actual = SECCIONES[pagina]
    preguntas = PREGUNTAS[area_actual]
    cliente = session['cliente']
    cliente_info = CLIENTES.get(cliente, {})

    if request.method == 'POST':
        respuestas_form = {}
        for i, pregunta in enumerate(preguntas):
            respuesta = request.form.get(f'{area_actual}_{i}')
            if not respuesta:
                error = "Por favor responde todas las preguntas antes de continuar."
                return render_template("encuesta.html", preguntas=preguntas, area=area_actual, escala=ESCALA,
                                          pagina=pagina, total=len(SECCIONES), error=error,
                                          cliente_logo=cliente_info['logo'], color_fondo=cliente_info['colorhex'], 
                                          cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")
            respuestas_form[f'{area_actual}_{i}'] = (area_actual, pregunta, respuesta)

        session['respuestas'].update(respuestas_form)

        if 'siguiente' in request.form:
            session['pagina'] += 1
        elif 'anterior' in request.form:
            session['pagina'] -= 1

        if session['pagina'] >= len(SECCIONES):
            conn = sqlite3.connect('respuestas.db')
            c = conn.cursor()
            for _, (area, pregunta, respuesta) in session['respuestas'].items():
                c.execute("INSERT INTO respuestas (cliente, area, pregunta, respuesta) VALUES (?, ?, ?, ?)",
                          (cliente, area, pregunta, respuesta))
            conn.commit()
            conn.close()
            session.clear()
            return render_template("gracias.html",
    		cliente_logo=cliente_info['logo'],
   		 cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png",
   		 color_fondo=cliente_info['colorhex']
					)

        return redirect(url_for('formulario'))

    return render_template("encuesta.html", preguntas=preguntas, area=area_actual, escala=ESCALA,
                              pagina=pagina, total=len(SECCIONES), error="",
                              cliente_logo=cliente_info['logo'], color_fondo=cliente_info['colorhex'], 
                              cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")

# ============================
# Sección: Inicio de la app Flask
# ============================
if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=10000, debug=True)
