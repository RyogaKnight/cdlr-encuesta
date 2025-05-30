from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

app = Flask(__name__)
app.secret_key = 'clave-super-secreta'

# ============================ CONEXIÓN GOOGLE SHEETS ============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ============================ FUNCIONES AUXILIARES ============================

def cargar_preguntas_activas(cliente, password):
    sheet = client.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    preguntas_sheet = sheet.worksheet("Preguntas")
    encuesta_sheet = sheet.worksheet("Encuesta")

    preguntas_data = preguntas_sheet.get_all_records()
    encuesta_data = encuesta_sheet.get_all_records()

    encuesta_cliente = next((e for e in encuesta_data if e['Clientes'].strip() == cliente and e['password'].strip() == password), None)
    if not encuesta_cliente or not encuesta_cliente.get('Preguntas'):
        return None

    preguntas_ids = [pid.strip() for pid in encuesta_cliente['Preguntas'].split(',')]
    preguntas = {}
    for pid in preguntas_ids:
        pregunta_row = next((p for p in preguntas_data if str(p['ID']).strip() == pid), None)
        if pregunta_row:
            area = pregunta_row['Area'].strip()
            preguntas.setdefault(area, []).append(pregunta_row['Pregunta'].strip())
    return preguntas

def cargar_clientes():
    sheet = client.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    hoja = sheet.worksheet("Clientes")
    clientes = hoja.get_all_records()
    return {cliente['Cliente']: cliente for cliente in clientes}

CLIENTES = cargar_clientes()
ESCALA = ["Nunca", "En ocasiones", "Con frecuencia", "Casi siempre", "Siempre"]

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

# ============================ RUTAS ============================

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        cliente_ingresado = request.form['cliente']
        password = request.form['password']
        cliente_info = CLIENTES.get(cliente_ingresado)
        if cliente_info and password == cliente_info['password']:
            preguntas = cargar_preguntas_activas(cliente_ingresado, password)
            if not preguntas:
                error = "No se encontraron preguntas activas para este cliente."
            else:
                session['autenticado'] = True
                session['cliente'] = cliente_ingresado
                session['pagina'] = 0
                session['respuestas'] = {}
                session['preguntas'] = preguntas
                return redirect(url_for('formulario'))
        else:
            error = "Cliente o contraseña incorrectos."
    return render_template("login.html", error=error)

@app.route('/encuesta', methods=['GET', 'POST'])
def formulario():
    if not session.get('autenticado'):
        return redirect(url_for('login'))

    cliente = session['cliente']
    preguntas_dict = session['preguntas']
    cliente_info = CLIENTES.get(cliente, {})
    secciones = list(preguntas_dict.keys())
    pagina = session.get('pagina', 0)

    if pagina >= len(secciones):
        return redirect(url_for('gracias'))

    area_actual = secciones[pagina]
    preguntas = preguntas_dict[area_actual]

    if request.method == 'POST':
        respuestas_form = {}
        for i, pregunta in enumerate(preguntas):
            respuesta = request.form.get(f'{area_actual}_{i}')
            if not respuesta:
                error = "Por favor responde todas las preguntas antes de continuar."
                return render_template("encuesta.html", preguntas=preguntas, area=area_actual, escala=ESCALA,
                                       pagina=pagina, total=len(secciones), error=error,
                                       cliente_logo=cliente_info['logo'], color_fondo=cliente_info['colorhex'],
                                       cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")
            respuestas_form[f'{area_actual}_{i}'] = (area_actual, pregunta, respuesta)

        session['respuestas'].update(respuestas_form)

        if 'siguiente' in request.form:
            session['pagina'] += 1
        elif 'anterior' in request.form:
            session['pagina'] -= 1

        if session['pagina'] >= len(secciones):
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
                                   color_fondo=cliente_info['colorhex'])

        return redirect(url_for('formulario'))

    return render_template("encuesta.html", preguntas=preguntas, area=area_actual, escala=ESCALA,
                           pagina=pagina, total=len(secciones), error="",
                           cliente_logo=cliente_info['logo'], color_fondo=cliente_info['colorhex'],
                           cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")

@app.route('/gracias')
def gracias():
    return render_template("gracias.html")

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=10000, debug=True)
