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
    firing_alerts = [a for a in alerts if a.get("status") == "firing"]
    resolved_alerts = [a for a in alerts if a.get("status") == "resolved"]

    if firing_alerts:
        message_lines.append(f"🚨 <b>ALARMAS ACTIVAS ({len(firing_alerts)})</b>\n")
        for alert in firing_alerts:
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            alertname = labels.get("alertname", "Sin nombre")
            severity = labels.get("severity", "")
            summary = annotations.get("summary", "")
            starts_at = alert.get("startsAt", "")  # Puedes formatear fecha si quieres
            sev_str = f"<u><b>P{severity}</b></u> " if severity else ""
            message_lines.append(f"{sev_str}<b>{alertname}</b>\n- {summary}\n- Inicio: {starts_at}\n")

    if resolved_alerts:
        message_lines.append(f"✅ <b>ALARMAS RESUELTAS ({len(resolved_alerts)})</b>\n")
        for alert in resolved_alerts:
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            alertname = labels.get("alertname", "Sin nombre")
            severity = labels.get("severity", "")
            summary = annotations.get("summary", "")
            ends_at = alert.get("endsAt", "")
            sev_str = f"<u><b>P{severity}</b></u> " if severity else ""
            message_lines.append(f"{sev_str}<b>{alertname}</b>\n- {summary}\n- Fin: {ends_at}\n")

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
        return {"status": "ok"}
    else:
        return {"status": "error", "detail": r.text}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



