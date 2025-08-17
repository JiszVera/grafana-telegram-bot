from flask import Flask, request
import requests
import os
from supabase import create_client, Client

app = Flask(__name__)

# Variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if not BOT_TOKEN:
    raise ValueError("Falta BOT_TOKEN en las variables de entorno.")

# Mapea las zonas a sus chat_id correspondientes
ZONA_CHAT_IDS = {
    "Norte": os.environ.get("CHAT_ID_NORTE"),  # por ejemplo: "123456789"
    "Sur": os.environ.get("CHAT_ID_SUR"),
}

def save_message(alertname, chat_id, message_id, status):
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

    # Extraer zona de las etiquetas y obtener chat_id correspondiente
    zona = labels.get("Zona")
    chat_id = ZONA_CHAT_IDS.get(zona)

    if not chat_id:
        print(f"No hay chat_id configurado para la zona '{zona}'")
        return {"status": "sin chat_id para zona"}

    if status == "firing":
        emoji = "🔴"
        title = "ALERTA ACTIVA"
    elif status == "resolved":
        emoji = "🟢"
        title = "ALERTA RESUELTA"
    else:
        return {"status": "estado desconocido"}

    text = f"{emoji} <b>{title}</b>\n\n{alertname}\n\n{summary}\n"

    prev_status, message_id = get_alert_status(alertname, chat_id)

    # Ignorar firing repetido
    if status == "firing" and prev_status == "firing":
        print(f"⚠️ Ignorado: '{alertname}' ya está en firing para {chat_id}")
        return {"status": "alerta firing repetida"}

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
