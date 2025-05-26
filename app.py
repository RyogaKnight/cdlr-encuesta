from flask import Flask, render_template_string, request

app = Flask(__name__)

PREGUNTAS = {
    "Planeación": [
        "Conozco claramente los objetivos estratégicos de la empresa.",
        "Sé cómo mi trabajo contribuye a los resultados de la organización.",
        "Recibo información oportuna sobre los cambios en la planeación.",
        "Participo en la toma de decisiones relacionadas con mi área."
    ],
    "Liderazgo": [
        "Mi líder reconoce mi trabajo de forma justa.",
        "Mi líder está disponible para orientarme.",
        "Recibo retroalimentación constructiva.",
        "Siento que se confía en mis capacidades."
    ],
    "Comunicación": [
        "La comunicación entre áreas es efectiva.",
        "Tengo canales claros para expresar sugerencias.",
        "Recibo la información necesaria para hacer mi trabajo.",
        "La información en la empresa es transparente."
    ],
    "Motivación": [
        "Me siento motivado a dar lo mejor de mí en el trabajo.",
        "Tengo oportunidades de crecimiento.",
        "Mis esfuerzos son valorados.",
        "Me entusiasma trabajar en esta empresa."
    ],
    "Reconocimiento": [
        "Se reconocen públicamente los logros.",
        "Existen incentivos por buen desempeño.",
        "Las promociones son justas y basadas en mérito.",
        "Siento que mi trabajo hace una diferencia."
    ]
}

ESCALA = ["Nunca", "En ocasiones", "Con frecuencia", "Casi siempre", "Siempre"]

@app.route("/", methods=["GET", "POST"])
def encuesta():
    if request.method == "POST":
        respuestas = request.form.to_dict()
        return render_template_string("""
        <h2>Gracias por completar la encuesta</h2>
        <p>Tu retroalimentación es muy valiosa.</p>
        <a href='/'>Volver</a>
        """)

    return render_template_string("""
    <html><head><title>Encuesta de Clima Laboral</title></head>
    <body style='font-family: sans-serif; max-width: 800px; margin: auto;'>
        <h1>Encuesta de Clima Laboral</h1>
        <form method='POST'>
            {% for area, preguntas in preguntas.items() %}
                <h2>{{ area }}</h2>
                {% for pregunta in preguntas %}
                    <p><strong>{{ pregunta }}</strong></p>
                    {% for opcion in escala %}
                        <label>
                            <input type='radio' name='{{ area }}_{{ loop.index }}' value='{{ opcion }}' required>
                            {{ opcion }}
                        </label><br>
                    {% endfor %}
                {% endfor %}
            {% endfor %}
            <br><input type='submit' value='Enviar'>
        </form>
    </body></html>
    """, preguntas=PREGUNTAS, escala=ESCALA)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
