from flask import Flask, request
import requests
import os
import json
from time import time
from supabase import create_client, Client

app = Flask(__name__)

# Variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_IDs = os.environ.get("CHAT_ID", "").split(",")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if not BOT_TOKEN or not CHAT_IDs:
    raise ValueError("Faltan BOT_TOKEN o CHAT_ID en las variables de entorno.")

# Filtro anti-repetición por alertname+chat_id
last_alert_time = {}

def save_message(alertname, chat_id, message_id):
    """Guardar en Supabase o actualizar si ya existe."""
    data = supabase.table("alerts").select("*").eq("alertname", alertname).eq("chat_id", chat_id).execute()
    if data.data:
        supabase.table("alerts").update({"message_id": message_id}).eq("alertname", alertname).eq("chat_id", chat_id).execute()
    else:
        supabase.table("alerts").insert({
            "alertname": alertname,
            "chat_id": chat_id,
            "message_id": message_id
        }).execute()

def get_message_id(alertname, chat_id):
    """Obtener message_id desde Supabase."""
    data = supabase.table("alerts").select("message_id").eq("alertname", alertname).eq("chat_id", chat_id).execute()
    if data.data:
        return data.data[0]["message_id"]
    return None

@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(force=True)

    # Logging para diagnosticar duplicados
    print("Payload recibido completo:")
    print(json.dumps(data, indent=2))

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
        now = time()
        for chat_id in CHAT_IDs:
            chat_id = chat_id.strip()
            key = f"{alertname}_{chat_id}"
            last_time = last_alert_time.get(key, 0)
            if now - last_time < 60:
                print(f"Ignorando alerta repetida '{alertname}' para chat {chat_id} en menos de 60 segundos")
                continue
            last_alert_time[key] = now

            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(send_url, json=payload)

            if r.status_code == 200:
                message_id = r.json()["result"]["message_id"]
                save_message(alertname, chat_id, message_id)
            else:
                print(f"Error al enviar mensaje a {chat_id}: {r.text}")

        return {"status": "alertas enviadas"}

    elif status == "resolved":
        for chat_id in CHAT_IDs:
            chat_id = chat_id.strip()
            message_id = get_message_id(alertname, chat_id)

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

            if r.status_code != 200:
                print(f"Error al editar mensaje para {alertname}, chat_id: {chat_id}: {r.text}")

        return {"status": "resuelto enviado"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)







