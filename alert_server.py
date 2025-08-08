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
    state = data.get("state")
    message = data.get("message", "Sin mensaje")

    if state == "firing":
        emoji = "🔴"
    elif state == "resolved":
        emoji = "🟢"
    else:
        emoji = "⚠️"

    text = f"{emoji} *Estado:* {state.upper()}\n📝 {message}"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    if last_message_id and state in ["firing", "resolved"]:
        # Editar mensaje existente
        edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload["message_id"] = last_message_id
        r = requests.post(edit_url, json=payload)
    else:
        # Enviar mensaje nuevo y guardar ID
        send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(send_url, json=payload)
        if r.status_code == 200:
            last_message_id = r.json()["result"]["message_id"]

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


