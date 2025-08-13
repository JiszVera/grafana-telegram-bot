from flask import Flask, request
import requests
import os
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

def save_message(alertname, chat_id, message_id, status):
    """Guardar o actualizar mensaje en Supabase."""
    data = supabase.table("alerts").select("*").eq("alertname", alertname).eq("chat_id", chat_id).execute()
    if data.data:
        supabase.table("alerts").update({
            "message_id": message_id,
            "status": status
        }).eq("alertname", alertname).eq("chat_id", chat_id).execute()
    else:
        supabase.table("alerts").insert({
            "alertname": alertname,
            "chat_id": chat_id,
            "message_id": message_id,
            "status": status
        }).execute()

def get_alert_status(alertname, chat_id):
    """Obtener estado y message_id de una alerta."""
    data = supabase.table("alerts").select("status, message_id").eq("alertname", alertname).eq("chat_id", chat_id).execute()
    if data.data:
        return data.data[0]["status"], data.data[0]["message_id"]
    return None, None

@app.route("/alert", methods=["POST"])
def alert():
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

    if status == "firing":
        emoji = "🔴"
        title = "ALERTA ACTIVA"
    elif status == "resolved":
        emoji = "🟢"
        title = "ALERTA RESUELTA"
    else:
        return {"status": "estado desconocido"}

    text = f"{emoji} <b>{title}</b>\n\n{alertname}\n\n{summary}\n"

    for chat_id in CHAT_IDs:
        chat_id = chat_id.strip()
        prev_status, message_id = get_alert_status(alertname, chat_id)

        # 🚫 Ignorar firing repetido
        if status == "firing" and prev_status == "firing":
            print(f"⚠️ Ignorado: '{alertname}' ya está en firing para {chat_id}")
            continue

        # Enviar nuevo firing
        if status == "firing":
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)
            if r.status_code == 200:
                message_id = r.json()["result"]["message_id"]
                save_message(alertname, chat_id, message_id, status)
            else:
                print(f"Error al enviar mensaje: {r.text}")

        # Editar a resuelto
        elif status == "resolved" and message_id:
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML"
            }
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json=payload)
            if r.status_code == 200:
                save_message(alertname, chat_id, message_id, status)
            else:
                print(f"Error al editar mensaje: {r.text}")

    return {"status": "procesado"}

@app.route("/ping", methods=["GET", "HEAD"])
def ping():
    return "", 200

@app.route("/")
def home():
    return "✅ Bot de Telegram para Grafana está en funcionamiento."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
