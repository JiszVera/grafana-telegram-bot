from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Obtener variables de entorno de forma segura
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en las variables de entorno.")

# Guardar el último ID de mensaje (memoria temporal)
last_message_id = None

@app.route("/")
def health_check():
    return "Bot en línea", 200

@app.route("/alert", methods=["POST"])
def alert():
    global last_message_id

    data = request.get_json(force=True)

    print("=== DATA RECIBIDA ===")
    print(data)
    print("=====================")

    # Datos de Grafana
    state = data.get("state", "unknown").lower()
    message = data.get("message", "Sin mensaje")
    labels = data.get("labels", {})
    annotations = data.get("annotations", {})
    grafana_reason = annotations.get("summary", "")

    # Filtrar mensaje innecesario (como 'power fail')
    if "power fail" in grafana_reason.lower():
        grafana_reason = "Evento detectado"

    # Personalización del mensaje
    titulo = "⚡Energia&Clima⚡"
    estado = "🔴 *Alarma activada:*" if state == "firing" else "✅ *Alarma resuelta:*"
    ubicacion = labels.get("location", "Ubicación desconocida")
    detalle = f"🚨{grafana_reason}🚨" if grafana_reason else "🚨Sin detalle🚨"

    text = f"{titulo}\n\n{estado}\n📍 {ubicacion}\n\n*Detalle:*\n{detalle}"

    print("=== MENSAJE A ENVIAR ===")
    print(text)
    print("========================")

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    # Enviar o editar mensaje en Telegram
    if last_message_id and state in ["firing", "resolved"]:
        edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload["message_id"] = last_message_id
        r = requests.post(edit_url, json=payload)
        print(f"Editar mensaje: status_code={r.status_code}, response={r.text}")
    else:
        send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(send_url, json=payload)
        print(f"Enviar mensaje: status_code={r.status_code}, response={r.text}")
        if r.status_code == 200:
            last_message_id = r.json()["result"]["message_id"]

    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



