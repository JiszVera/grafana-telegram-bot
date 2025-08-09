import os
from flask import Flask, request
import requests

app = Flask(__name__)

# Obtener el BOT_TOKEN y CHAT_IDS desde las variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_IDS = os.environ.get("CHAT_IDS")

# Verificar que las variables se cargaron correctamente
if not BOT_TOKEN:
    raise ValueError("Falta el BOT_TOKEN en las variables de entorno.")
if not CHAT_IDS:
    raise ValueError("Falta el CHAT_IDS en las variables de entorno.")

# Convertir CHAT_IDS en una lista
CHAT_IDS = CHAT_IDS.split(",")  # Dividir la cadena por comas para obtener una lista

# Asegurarse de que todos los chat IDs estén correctamente formateados
CHAT_IDS = [chat_id.strip() for chat_id in CHAT_IDS]  # Eliminar espacios extras

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
    text = f"{emoji} <b>{title}</b>\n\n{alertname}\n\n{summary}\n"

    # Si es firing, enviamos nuevo mensaje a todos los canales y guardamos message_id
    if status == "firing":
        for chat_id in CHAT_IDS:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(send_url, json=payload)

            if r.status_code == 200:
                resp = r.json()
                message_id = resp["result"]["message_id"]
                message_store[alertname] = message_id
            else:
                return {"status": "error al enviar", "detail": r.text}, 500

        return {"status": "alerta enviada", "message_id": message_id}

    # Si es resolved, editamos mensaje anterior (si existe)
    elif status == "resolved":
        message_id = message_store.get(alertname)
        if not message_id:
            return {"status": "no se encontró message_id para editar"}

        for chat_id in CHAT_IDS:
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML"
            }
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            r = requests.post(edit_url, json=payload)

            if r.status_code != 200:
                return {"status": "error al editar", "detail": r.text}, 500

        return {"status": "mensaje editado"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)















