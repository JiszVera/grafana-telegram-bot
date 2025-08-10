from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Obtener variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_IDs = os.environ.get("CHAT_ID", "").split(",")  # Lista separada por coma

if not BOT_TOKEN or not CHAT_IDs:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en las variables de entorno.")

# Diccionario en memoria: {alertname: {chat_id: message_id}}
message_store = {}

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

    # Estado visual
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
        message_store[alertname] = {}  # Inicializar diccionario por alerta
        for chat_id in CHAT_IDs:
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
                message_store[alertname][chat_id] = message_id  # Guardar por chat_id
                print(f"[FIRING] Enviado a {chat_id}, message_id: {message_id}")
            else:
                print(f"[FIRING ERROR] {chat_id}: {r.text}")
                return {"status": "error al enviar", "detail": r.text}, 500

        return {"status": "alertas enviadas"}

    elif status == "resolved":
        if alertname not in message_store:
            print(f"[RESOLVED] No se encontró message_id para: {alertname}")
            return {"status": "no se encontró message_id para editar"}

        failed = []
        for chat_id in CHAT_IDs:
            message_id = message_store[alertname].get(chat_id)
            if not message_id:
                print(f"[RESOLVED] No hay message_id para chat {chat_id}")
                failed.append(chat_id)
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
                print(f"[RESOLVED] Editado en {chat_id}, msg_id: {message_id}")
            else:
                print(f"[RESOLVED ERROR] {chat_id}: {r.text}")
                failed.append(chat_id)

        if failed:
            return {"status": "error parcial", "failed_chats": failed}, 207

        return {"status": "mensajes editados"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
