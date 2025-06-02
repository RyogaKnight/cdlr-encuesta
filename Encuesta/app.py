# ---------------------------- app.py ----------------------------
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
import os
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
import logging

app = Flask(__name__)
app.secret_key = 'clave-super-secreta'
logging.basicConfig(level=logging.INFO)

# Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client_gsheets = gspread.authorize(creds)

# Supabase
SUPABASE_URL = os.environ["SUPABASE_PROJECT_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def cargar_clientes():
    sheet = client_gsheets.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    hoja = sheet.worksheet("Clientes")
    registros = hoja.get_all_records()
    return {fila['Cliente']: fila for fila in registros}

def cargar_preguntas_para_cliente(cliente, password):
    sheet = client_gsheets.open_by_key("1v6yY39CcjQR1KnZHDRdr3VGLG7-CVbBmigTh399RDEs")
    preguntas = sheet.worksheet("Preguntas").get_all_records()
    encuestas = sheet.worksheet("Encuestas").get_all_records()
    clientes = sheet.worksheet("Clientes").get_all_records()

    encuesta = next((e for e in encuestas if e["Activo"].strip().lower() == "yes" and e["Cliente"].strip() == cliente), None)
    if not encuesta:
        return None

    cliente_data = next((c for c in clientes if c["Cliente"].strip() == cliente and c["Password"].strip() == password), None)
    if not cliente_data:
        return None

    session['encuesta_id'] = int(encuesta["ID"])
    ids = [pid.strip() for pid in encuesta["Preguntas"].split(',')]

    preguntas_por_area = {}
    for pid in ids:
        fila = next((p for p in preguntas if str(p["ID"]).strip() == pid), None)
        if fila:
            area = fila["Area"].strip()
            tipo = fila.get("Tipo", "Frecuencia").strip()
            texto = fila["Pregunta"].strip()
            preguntas_por_area.setdefault(area, []).append({
                "texto": texto,
                "tipo": tipo
            })

    # Reordenar áreas poniendo "General" al final
    areas = list(preguntas_por_area.keys())
    if "General" in areas:
        areas.remove("General")
        areas.append("General")

    preguntas_ordenadas = {area: preguntas_por_area[area] for area in areas}
    return preguntas_ordenadas

ESCALA = ["Nunca", "En ocasiones", "Con frecuencia", "Casi siempre", "Siempre"]

def guardar_respuesta_en_supabase(encuesta_id, cliente, area, pregunta, respuesta):
    try:
        data = {
            "encuesta": encuesta_id,
            "cliente": cliente,
            "area": area,
            "pregunta": pregunta,
            "respuesta": respuesta
        }
        result = supabase.table("respuestas").insert(data).execute()
        logging.info("\u2705 Respuesta guardada: %s", result)
        return True
    except Exception as e:
        logging.error("\u274c Error al guardar en Supabase: %s", e)
        return False

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        cliente = request.form['cliente']
        password = request.form['password']

        preguntas = cargar_preguntas_para_cliente(cliente, password)
        if preguntas:
            session['autenticado'] = True
            session['cliente'] = cliente
            session['pagina'] = 0
            session['respuestas'] = {}
            session['preguntas'] = preguntas
            session['orden_areas'] = list(preguntas.keys())
            return redirect(url_for('formulario'))
        else:
            error = "Cliente, contrase\u00f1a o configuraci\u00f3n incorrecta."
    return render_template("login.html", error=error)

@app.route('/encuesta', methods=['GET', 'POST'])
def formulario():
    if not session.get('autenticado'):
        return redirect(url_for('login'))

    cliente = session['cliente']
    preguntas_dict = session['preguntas']
    secciones = session['orden_areas']
    pagina = session.get('pagina', 0)

    if pagina >= len(secciones):
        return redirect(url_for('gracias'))

    area = secciones[pagina]
    preguntas = preguntas_dict[area]
    cliente_info = CLIENTES.get(cliente, {"Logo": "", "Colorhex": "#FFFFFF"})

    if request.method == 'POST':
        respuestas_form = {}
        incompleta = False

        for i, pregunta in enumerate(preguntas):
            clave = f'{area}_{i}'
            respuesta = request.form.get(clave, '').strip()
            if not respuesta:
                incompleta = True
            respuestas_form[clave] = (area, pregunta["texto"], respuesta)

        for k, v in respuestas_form.items():
            session['respuestas'][k] = v

        if incompleta:
            return render_template("encuesta.html", preguntas=preguntas, area=area, escala=ESCALA,
                pagina=pagina, total=len(secciones), error="", respuestas_guardadas={k: v[2] for k, v in session['respuestas'].items() if k.startswith(area)},
                cliente_logo=cliente_info["Logo"], color_fondo=cliente_info["Colorhex"],
                cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")

        if 'siguiente' in request.form:
            session['pagina'] += 1
        elif 'anterior' in request.form:
            session['pagina'] -= 1
        return redirect(url_for('formulario'))

    respuestas_guardadas = {k: v[2] for k, v in session.get('respuestas', {}).items() if k.startswith(area)}
    return render_template("encuesta.html", preguntas=preguntas, area=area, escala=ESCALA,
        pagina=pagina, total=len(secciones), error="", respuestas_guardadas=respuestas_guardadas,
        cliente_logo=cliente_info["Logo"], color_fondo=cliente_info["Colorhex"],
        cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png")

@app.route('/gracias')
def gracias():
    cliente = session.get('cliente', '')
    cliente_info = CLIENTES.get(cliente, {"Logo": "", "Colorhex": "#FFFFFF"})
    respuestas = session.get('respuestas', {})
    errores = False
    encuesta_id = session.get('encuesta_id', 1)

    for _, (area, pregunta, respuesta) in respuestas.items():
        exito = guardar_respuesta_en_supabase(encuesta_id, cliente, area, pregunta, respuesta)
        if not exito:
            errores = True

    session.clear()

    return render_template("gracias.html", cliente_logo=cliente_info["Logo"],
        color_fondo=cliente_info["Colorhex"], cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png",
        errores=errores)

if __name__ == '__main__':
    CLIENTES = cargar_clientes()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
