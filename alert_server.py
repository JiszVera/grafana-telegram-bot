from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# Variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_IDs = os.environ.get("CHAT_ID", "").split(",")

if not BOT_TOKEN or not CHAT_IDs:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en las variables de entorno.")

# Ruta persistente en Render
STORE_FILE = "/var/data/message_store.json"

# Crear carpeta persistente si no existe
os.makedirs("/var/data", exist_ok=True)

# Cargar almacenamiento persistente de message_ids
def load_store():
    try:
        with open(STORE_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_store(store):
    with open(STORE_FILE, "w") as f:
        json.dump(store, f)

# Cargar datos al iniciar
message_store = load_store()

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

    # Crear texto del mensaje
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
            else:
                print(f"Error al enviar mensaje a {chat_id}: {r.text}")

        save_store(message_store)
        return {"status": "alertas enviadas"}

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

            if r.status_code != 200:
                print(f"Error al editar mensaje para {alertname}, message_id: {message_id}, chat_id: {chat_id}: {r.text}")

        save_store(message_store)
        return {"status": "resuelto enviado"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



