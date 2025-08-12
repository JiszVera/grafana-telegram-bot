from flask import Flask, request
from supabase import create_client
from datetime import datetime, timedelta, timezone
import os
import requests

# Configuración desde variables de entorno en Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# Tiempo mínimo para reenviar la misma alerta
MIN_TIME_BETWEEN_ALERTS = timedelta(minutes=2)

def should_send(alertname, chat_id, fingerprint):
    """Decide si enviar o no la alerta."""
    data = supabase.table("alerts") \
        .select("fingerprint, last_sent") \
        .eq("alertname", alertname) \
        .eq("chat_id", chat_id) \
        .execute()

    if not data.data:
        return True  # No hay registros, enviar

    row = data.data[0]
    last_fp = row.get("fingerprint")
    last_sent_str = row.get("last_sent")
    last_sent = None

    if last_sent_str:
        try:
            last_sent = datetime.fromisoformat(last_sent_str.replace("Z", "+00:00"))
        except:
            pass

    now = datetime.now(timezone.utc)

    # Si fingerprint es distinto → enviar
    if last_fp != fingerprint:
        return True
    # Si pasó el tiempo mínimo → enviar
    if last_sent and now - last_sent > MIN_TIME_BETWEEN_ALERTS:
        return True

    return False

def save_message(alertname, chat_id, message_id, status, fingerprint):
    """Guarda o actualiza el registro en Supabase."""
    supabase.table("alerts").upsert({
        "alertname": alertname,
        "chat_id": chat_id,
        "message_id": message_id,
        "status": status,
        "fingerprint": fingerprint,
        "last_sent": datetime.now(timezone.utc).isoformat()
    }).execute()

def send_telegram_message(chat_id, text):
    """Envía mensaje a Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=payload)
    return resp.json().get("result", {}).get("message_id")

def edit_telegram_message(chat_id, message_id, text):
    """Edita mensaje existente en Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    requests.post(url, json=payload)

@app.route("/alert", methods=["POST"])
def alert():
    alert_data = request.json
    status = alert_data["status"]
    alertname = alert_data["alerts"][0]["labels"]["alertname"]
    fingerprint = alert_data["alerts"][0].get("fingerprint", "")
    message_text = alert_data["alerts"][0]["annotations"]["description"]

    # Lista de chats a notificar
    chat_ids = ["123456789", "987654321"]  # Reemplazar por tus chats reales

    for chat_id in chat_ids:
        if status == "firing":
            if should_send(alertname, chat_id, fingerprint):
                message_id = send_telegram_message(chat_id, f"🚨 ALERTA: {message_text}")
                save_message(alertname, chat_id, message_id, status, fingerprint)
            else:
                print(f"⏳ Firing {alertname} para {chat_id} bloqueado por duplicado reciente")

        elif status == "resolved":
            data = supabase.table("alerts") \
                .select("message_id") \
                .eq("alertname", alertname) \
                .eq("chat_id", chat_id) \
                .execute()

            if data.data:
                message_id = data.data[0]["message_id"]
                edit_telegram_message(chat_id, message_id, f"✅ RESUELTO: {message_text}")
                save_message(alertname, chat_id, message_id, status, fingerprint)

    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)








