from flask import Flask, request
import requests
import os
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_IDs = os.environ.get("CHAT_ID", "").split(",")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_message(alertname, chat_id, message_id, status):
    # Tu código existente aquí (sin cambios)

def get_message_id(alertname, chat_id):
    # Tu código existente aquí (sin cambios)

def update_last_sent(alertname, chat_id):
    now = datetime.utcnow().isoformat()
    supabase.table("alerts").update({"last_sent": now}).eq("alertname", alertname).eq("chat_id", chat_id).execute()

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

    if status == "firing":
        for chat_id in CHAT_IDs:
            chat_id = chat_id.strip()
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(send_url, json=payload)
            if r.status_code == 200:
                message_id = r.json()["result"]["message_id"]
                save_message(alertname, chat_id, message_id, status)
                update_last_sent(alertname, chat_id)
    elif status == "resolved":
        for chat_id in CHAT_IDs:
            chat_id = chat_id.strip()
            message_id = get_message_id(alertname, chat_id)
            if not message_id:
                continue
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML"
            }
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            r = requests.post(edit_url, json=payload)
            if r.status_code == 200:
                update_last_sent(alertname, chat_id)

    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

