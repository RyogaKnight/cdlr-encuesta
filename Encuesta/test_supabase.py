import os
import psycopg2

# Obtener cadena de conexión desde variable de entorno
SUPABASE_URL = os.environ["SUPABASE_URL"]

try:
    conn = psycopg2.connect(SUPABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("✅ Conexión exitosa a Supabase:", result)
    conn.close()
except Exception as e:
    print("❌ Error al conectar a Supabase:", e)