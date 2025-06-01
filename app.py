<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Encuesta</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: {{ color_fondo }};
      padding: 40px;
    }

    .contenedor {
      background-color: white;
      padding: 40px;
      border-radius: 10px;
      max-width: 800px;
      margin: auto;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    }

    h2 {
      color: #333;
    }

    .pregunta {
      margin-bottom: 20px;
    }

    .escala, .score {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 10px;
    }

    .score input[type="number"] {
      width: 60px;
      padding: 5px;
    }

    textarea {
      width: 100%;
      height: 100px;
      padding: 10px;
      margin-top: 10px;
    }

    .botones {
      margin-top: 30px;
      display: flex;
      justify-content: space-between;
    }

    button {
      padding: 10px 20px;
      background-color: #0066cc;
      color: white;
      border: none;
      border-radius: 5px;
      cursor: pointer;
    }

    .logos {
      display: flex;
      justify-content: center;
      gap: 60px;
      margin-top: 40px;
    }

    .logos img {
      height: 80px;
    }

    .error {
      color: red;
      font-weight: bold;
    }

    @media (max-width: 600px) {
      .score input[type="number"] {
        width: 40px;
      }

      button {
        width: 100%;
        margin-bottom: 10px;
      }

      .logos {
        flex-direction: column;
        gap: 20px;
      }
    }
  </style>
</head>
<body>
  <div class="contenedor">
    <h2>Sección: {{ area }}</h2>

    {% if error %}
      <p class="error">{{ error }}</p>
    {% endif %}

    <form method="post">
      {% for i, pregunta in enumerate(preguntas) %}
        <div class="pregunta">
          <p><strong>{{ i + 1 }}. {{ pregunta.texto }}</strong></p>

          {% if pregunta.tipo == 'Frecuencia' %}
            <div class="escala">
              {% for opcion in escala %}
                <label>
                  <input type="radio" name="{{ area }}_{{ i }}" value="{{ opcion }}">
                  {{ opcion }}
                </label>
              {% endfor %}
            </div>

          {% elif pregunta.tipo == 'Score' %}
            <div class="score">
              <input type="number" name="{{ area }}_{{ i }}" min="1" max="10" placeholder="1 a 10">
            </div>

          {% elif pregunta.tipo == 'Abierta' %}
            <textarea name="{{ area }}_{{ i }}" placeholder="Escribe tu respuesta..."></textarea>
          {% endif %}
        </div>
      {% endfor %}

      <div class="botones">
        {% if pagina > 0 %}
          <button type="submit" name="anterior">Anterior</button>
        {% endif %}
        <button type="submit" name="siguiente">Siguiente</button>
      </div>
    </form>

    <div class="logos">
      <img src="{{ cliente_logo }}" alt="Logo Cliente">
      <img src="{{ cdlr_logo }}" alt="Logo CDLR">
    </div>
  </div>
</body>
</html>
