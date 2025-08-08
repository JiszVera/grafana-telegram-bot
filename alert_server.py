from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

last_message_id = None

@app.route("/alert", methods=["POST"])
def alert():
    global last_message_id

    data = request.json

    # Datos de Grafana
    state = data.get("state", "unknown")
    message = data.get("message", "Sin mensaje")
    labels = data.get("labels", {})
    annotations = data.get("annotations", {})
    grafana_reason = annotations.get("summary", "Sin detalle")

    # Personaliza el mensaje
    titulo = "⚡Energia&Clima⚡"
    estado = "🔴 Alarma activada:" if state.lower() == "firing" else "✅ Alarma resuelta:"
    ubicacion = labels.get("location", "Ubicación desconocida")
    detalle = detalle = f"🚨{grafana_reason}🚨"

    text = f"{titulo}\n\n{estado}\n{ubicacion}\n\nDetalle:\n{detalle}"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    # Edita mensaje anterior si hay
    if last_message_id:
        edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload["message_id"] = last_message_id
        requests.post(edit_url, json=payload)
    else:
        send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(send_url, json=payload)
        if r.status_code == 200:
            last_message_id = r.json()["result"]["message_id"]

    return {"status": "ok"}


