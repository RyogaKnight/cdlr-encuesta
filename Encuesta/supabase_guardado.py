
import psycopg2
import os

# ============================ FUNCIÓN PARA GUARDAR RESPUESTAS EN SUPABASE ============================

def guardar_respuesta_en_supabase(cliente, area, pregunta, respuesta, encuesta_id):
    """
    Inserta una respuesta individual en la base de datos PostgreSQL (Supabase).
    """
    try:
        conn = psycopg2.connect(os.environ["SUPABASE_URL"])
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO respuestas (cliente, area, pregunta, respuesta, encuesta)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (cliente, area, pregunta, respuesta, encuesta_id)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Error al guardar en Supabase:", e)


# Reemplaza en app.py este bloque:

        if session['pagina'] >= len(secciones):
            for _, (area, pregunta, respuesta) in session['respuestas'].items():
                guardar_respuesta_en_supabase(cliente, area, pregunta, respuesta, encuesta_id=1)  # Usa el ID real
            session.clear()
            return render_template("gracias.html",
                                   cliente_logo=cliente_info["Logo"],
                                   cdlr_logo="https://iskali.com.mx/wp-content/uploads/2025/05/CDLR.png",
                                   color_fondo=cliente_info["Colorhex"])
