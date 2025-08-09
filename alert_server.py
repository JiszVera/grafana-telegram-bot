from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en las variables de entorno.")

# Diccionario en memoria para asociar alertname -> message_id
message_store = {}

@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(force=True)
    alerts = data.get("alerts", [])

    if not alerts:
        return {"status": "no alerts"}

    # Solo procesamos la primera alerta
    alert = alerts[0]
    status = alert.get("status")
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get("alertname", "Sin nombre")
    summary = annotations.get("summary", "🚨GRUPO EN SERVICIO🚨")  # Fijo si no viene
    external_url = data.get("externalURL", "")

    # Crear mensaje base (emoji depende del estado)
    if status == "firing":
        emoji = "🔴"
        title = "ALERTA ACTIVA"
    elif status == "resolved":
        emoji = "🟢"
        title = "ALERTA RESUELTA"
    else:
        return {"status": "estado desconocido"}

    # Formar el texto del mensaje
    text = f"{emoji} <b>{title}</b>\n\n🏢 {alertname}\n\n- {summary}\n"
    if external_url:
        text += f'<a href="{external_url}">📲 Ver en Grafana</a>'

    # Si es firing, enviamos nuevo mensaje y guardamos message_id
    if status == "firing":
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(send_url, json=payload)

        if r.status_code == 200:
            resp = r.json()
            message_id = resp["result"]["message_id"]
            message_store[alertname] = message_id
            return {"status": "alerta enviada", "message_id": message_id}
        else:
            return {"status": "error al enviar", "detail": r.text}, 500

    # Si es resolved, editamos mensaje anterior (si existe)
    elif status == "resolved":
        message_id = message_store.get(alertname)
        if not message_id:
            return {"status": "no se encontró message_id para editar"}

        payload = {
            "chat_id": CHAT_ID,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        r = requests.post(edit_url, json=payload)

        if r.status_code == 200:
            return {"status": "mensaje editado"}
        else:
            return {"status": "error al editar", "detail": r.text}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port) #esta la plantilla de donde proviene la alerta











