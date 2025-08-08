from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en las variables de entorno.")

@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(force=True)
    alerts = data.get("alerts", [])

    if not alerts:
        return {"status": "no alerts"}

    message_lines = []

    # Solo tomamos la primera alerta por simplicidad
    alert = alerts[0]
    status = alert.get("status")

    if status == "firing":
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alertname = labels.get("alertname", "Sin nombre")
        severity = labels.get("severity", "")
        summary = annotations.get("summary", "")
        sev_str = f"<u><b>P{severity}</b></u> " if severity else ""

        message_lines.append(f"🔴 <b>ALERTA ACTIVA</b>\n")
        message_lines.append(f"{sev_str}<b>{alertname}</b>\n")
        if summary:
            message_lines.append(f"- {summary}")

        external_url = data.get("externalURL", "")
        if external_url:
            message_lines.append(f'<a href="{external_url}">📲 Ver en Grafana</a>')

        text = "\n".join(message_lines)

        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }

        send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(send_url, json=payload)

        if r.status_code == 200:
            return {"status": "alerta enviada"}
        else:
            return {"status": "error", "detail": r.text}, 500

    elif status == "resolved":
        # Ignoramos alerta resuelta (no enviamos nada)
        return {"status": "alerta resuelta ignorada"}

    else:
        return {"status": "estado desconocido"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)




