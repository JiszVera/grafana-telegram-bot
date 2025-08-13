from flask import Flask, request
import requests
import os
import json
from supabase import create_client, Client

app = Flask(__name__)

# Variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_IDs = list(set(chat_id.strip() for chat_id in os.environ.get("CHAT_ID", "").split(",") if chat_id.strip()))
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if not BOT_TOKEN or not CHAT_IDs:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en las variables de entorno.")

def save_message(alertname, chat_id, message_id, status):
    """Guardar o actualizar mensaje en Supabase de forma atómica."""
    print(f"Guardando mensaje (upsert): alertname={alertname}, chat_id={chat_id}, message_id={message_id}, status={status}")
    supabase.table("alerts").upsert({
        "alertname": alertname,
        "chat_id": chat_id,
        "message_id": message_id,
        "status": status
    }, on_conflict=["alertname", "chat_id"]).execute()

def get_message_id(alertname, chat_id):
    data = supabase.table("alerts").select("message_id").eq("alertname", alertname).eq("chat_id", chat_id).execute()
    if data.data:
        return data.data[0]["message_id"]
    return None

def is_alert_already_sent(alertname, chat_id):
    """Verifica si ya se envió una alerta 'firing' para evitar duplicados."""
    data = supabase.table("alerts").select("status").eq("alertname", alertname).eq("chat_id", chat_id).execute()
    if data.data and data.data[0]["status"] == "firing":
        return True
    return False

@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200

@app.route("/alert", methods=["POST"])
def alert():

@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(force=True)
    alerts = data.get("alerts", [])

    if not alerts:
        print("No hay alertas en el payload recibido")
        return {"status": "no alerts"}

    alert = alerts[0]
    status = alert.get("status")
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    alertname = labels.get("alertname", "Sin nombre")
    summary = annotations.get("summary", "🚨GRUPO EN SERVICIO🚨")

    print(f"Alerta recibida: alertname={alertname}, status={status}")

    if status == "firing":
        emoji = "🔴"
        title = "ALERTA ACTIVA"
    elif status == "resolved":
        emoji = "🟢"
        title = "ALERTA RESUELTA"
    else:
        print(f"Estado desconocido: {status}")
        return {"status": "estado desconocido"}

    text = f"{emoji} <b>{title}</b>\n\n{alertname}\n\n{summary}\n"

    if status == "firing":
        for chat_id in CHAT_IDs:
            chat_id = chat_id.strip()

            # Evita duplicados si ya se envió
            if is_alert_already_sent(alertname, chat_id):
                print(f"Alerta ya fue enviada, se omite: alertname={alertname}, chat_id={chat_id}")
                continue

            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(send_url, json=payload)
            print(f"Enviando firing a chat_id={chat_id}, status_code={r.status_code}")

            if r.status_code == 200:
                message_id = r.json()["result"]["message_id"]
                save_message(alertname, chat_id, message_id, status)
            else:
                print(f"Error al enviar mensaje a {chat_id}: {r.text}")

        return {"status": "alertas enviadas"}

    elif status == "resolved":
        for chat_id in CHAT_IDs:
            chat_id = chat_id.strip()
            message_id = get_message_id(alertname, chat_id)

            if not message_id:
                print(f"No se encontró message_id para alertname={alertname}, chat_id={chat_id}")
                continue

            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML"
            }
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            r = requests.post(edit_url, json=payload)

            print(f"Intentando editar mensaje para chat_id={chat_id}, message_id={message_id}, status_code={r.status_code}")
            if r.status_code == 200:
                save_message(alertname, chat_id, message_id, status)
            else:
                print(f"Error al editar mensaje: {r.text}")

        return {"status": "resuelto enviado"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

