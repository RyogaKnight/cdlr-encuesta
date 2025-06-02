from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# Configuración de tu base de datos en Bluehost
db_config = {
    'host': 'box5130.bluehost.com',
    'user': 'noresteb_cdlradmin',
    'password': 'Lcvb390DB@123',
    'database': 'noresteb_cdlrencuesta'
}

@app.route('/api/guardar', methods=['POST'])
def guardar():
    data = request.json  # esperamos un JSON como {'cliente':..., 'area':..., 'pregunta':..., 'respuesta':...}

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        sql = "INSERT INTO respuestas (cliente, area, pregunta, respuesta) VALUES (%s, %s, %s, %s)"
        valores = (data['cliente'], data['area'], data['pregunta'], data['respuesta'])

        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Guardado exitoso'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5005)
