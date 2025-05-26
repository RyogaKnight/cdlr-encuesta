from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Configuracion basica
@app.route("/")
def home():
    return "<h1>Bienvenido a la encuesta de Clima Laboral - CDLR</h1>"

# Ruta protegida por contraseña generica (simple, para MVP)
@app.route("/encuesta", methods=["GET", "POST"])
def encuesta():
    password = "CDLR2025"
    if request.method == "POST":
        ingreso = request.form.get("clave")
        if ingreso == password:
            return redirect(url_for("formulario"))
        else:
            return "<h3>Contraseña incorrecta</h3><a href='/encuesta'>Volver</a>"
    return '''
        <form method="POST">
            <label>Ingresa la clave para acceder a la encuesta:</label><br>
            <input type="password" name="clave">
            <input type="submit" value="Entrar">
        </form>
    '''

# Formulario simulado (por ahora)
@app.route("/formulario")
def formulario():
    return "<h2>Formulario de encuesta (aqui ira el HTML real)</h2>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
