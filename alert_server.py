from flask import Flask, request
import requests
import os
import json
from supabase import create_client, Client

app = Flask(__name__)

# Variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_IDs = os.environ.get("CHAT_ID", "").split(",")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if not BOT_TOKEN or not CHAT_IDs:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en las variables de entorno.")

# =============================
# Funciones para almacenar datos en Supabase
# =============================

def load_store():
    """Carga el diccionario de message_store desde Supabase."""
    try:
        res = supabase.table("alert_store").select("*").execute()
        store = {}
        for row in res.data:
            alertname = row["alertname"]
            chat_id = row["chat_id"]
            message_id = row["message_id"]
            if alertname not in store:
                store[alertname] = {}
            store[alertname][chat_id] = message_id
        return store
    except Exception as e:
        print("Error cargando datos de Supabase:", e)
        return {}

def save_message(alertname, chat_id, message_id):
    """Guarda o actualiza un registro en Supabase."""
    try:
        supabase.table("alert_store").upsert({
            "alertname": alertname,
            "chat_id": chat_id,
            "message_id": message_id
        }).execute()
    except Exception as e:
        print("Error guardando en Supabase:", e)

def delete_message(alertname):
    """Elimina todos los registros de un alertname."""
    try:
        supabase.table("alert_store").delete().eq("alertname", alertname).execute()
    except Exception as e:
        print("Error eliminando en Supabase:", e)

# Cargar datos iniciales
message_store = load_store()

# =============================
# RUTA PRINCIPAL
# =============================
@app.route("/alert", methods=["POST"])
def alert():
    global message_store
    data = request.get_json(force=True)
    alerts = data.get("alerts", [])

    if not alerts:
        return {"status": "no alerts"}

    alert = alerts[0]
    status = alert.get("status")
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    alertname = labels.get("alertname", "Sin nombre")
    summary = annotations.get("summary", "🚨GRUPO EN SERVICIO🚨")

    # Texto del mensaje
    if status == "firing":
        emoji = "🔴"
        title = "ALERTA ACTIVA"
    elif status == "resolved":
        emoji = "🟢"
        title = "ALERTA RESUELTA"
    else:
        return {"status": "estado desconocido"}

    text = f"{emoji} <b>{title}</b>\n\n{alertname}\n\n{summary}\n"

    # =============================
    # ALERTA ACTIVA
    # =============================
    if status == "firing":
        message_store[alertname] = {}
        for chat_id in CHAT_IDs:
            chat_id = chat_id.strip()
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(send_url, json=payload)

            print(f"Enviando alerta a chat_id: {chat_id}")
            print("Payload de envío:", payload)
            print("Respuesta de Telegram:", r.status_code, "-", r.text)

            if r.status_code == 200:
                message_id = r.json()["result"]["message_id"]
                message_store[alertname][chat_id] = message_id
                save_message(alertname, chat_id, message_id)  # Guardar en Supabase
            else:
                print(f"Error al enviar mensaje a {chat_id}: {r.text}")

        return {"status": "alertas enviadas"}

    # =============================
    # ALERTA RESUELTA
    # =============================
    elif status == "resolved":
        if alertname not in message_store:
            return {"status": "alerta no encontrada para editar"}

        for chat_id in CHAT_IDs:
            chat_id = chat_id.strip()
            message_id = message_store[alertname].get(chat_id)

            if not message_id:
                print(f"No se encontró message_id para {alertname} en {chat_id}")
                continue

            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML"
            }
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            r = requests.post(edit_url, json=payload)

            print(f"Intentando editar el mensaje con message_id: {message_id}")
            print(f"Respuesta de Telegram al intentar editar para {chat_id}: {r.status_code} - {r.text}")

            if r.status_code == 200:
                delete_message(alertname)  # Eliminar de Supabase cuando se resuelve
            else:
                print(f"Error al editar mensaje para {alertname}, chat_id: {chat_id}: {r.text}")

        return {"status": "resuelto enviado"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)




