from flask import Flask, request
import requests
import os
from supabase import create_client, Client
import threading

app = Flask(__name__)

# ENV variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if not BOT_TOKEN:
    raise ValueError("Falta BOT_TOKEN en las variables de entorno.")

ZONA_CHAT_IDS = {
    "Norte": os.environ.get("CHAT_ID_NORTE"),
    "Sur": os.environ.get("CHAT_ID_SUR"),
}

# Normaliza el summary para evitar duplicados por espacios o mayúsculas
def normalize_summary(summary: str) -> str:
    return summary.strip().lower()

def save_message(alertname, chat_id, summary, message_id, status):
    summary = normalize_summary(summary)
    data = supabase.table("alerts").select("*") \
        .eq("alertname", alertname) \
        .eq("chat_id", chat_id) \
        .eq("summary", summary).execute()

    if data.data:
        supabase.table("alerts").update({
            "message_id": message_id,
            "status": status
        }).eq("alertname", alertname) \
         .eq("chat_id", chat_id) \
         .eq("summary", summary).execute()
    else:
        supabase.table("alerts").insert({
            "alertname": alertname,
            "chat_id": chat_id,
            "summary": summary,
            "message_id": message_id,
            "status": status
        }).execute()

def get_alert_status(alertname, chat_id, summary):
    summary = normalize_summary(summary)
    data = supabase.table("alerts").select("status, message_id") \
        .eq("alertname", alertname) \
        .eq("chat_id", chat_id) \
        .eq("summary", summary).execute()

    if data.data:
        return data.data[0]["status"], data.data[0]["message_id"]
    return None, None

def procesar_alerta(alert):
    try:
        status = alert.get("status")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alertname = labels.get("alertname", "Sin nombre")
        raw_summary = annotations.get("summary", "🚨GRUPO EN SERVICIO🚨")
        summary = normalize_summary(raw_summary)
        zona = labels.get("Zona")
        chat_id = ZONA_CHAT_IDS.get(zona)

        if not chat_id:
            print(f"⚠️ No hay chat_id configurado para la zona '{zona}'")
            return

        if status == "firing":
            emoji = "🔴"
            title = "ALERTA ACTIVA"
        elif status == "resolved":
            emoji = "🟢"
            title = "ALERTA RESUELTA"
        else:
            print(f"⚠️ Estado desconocido para alerta: {status}")
            return

        text = f"{emoji} <b>{title}</b>\n\n{alertname}\n\n{raw_summary}\n"

        prev_status, message_id = get_alert_status(alertname, chat_id, raw_summary)

        if status == "firing" and prev_status == "firing":
            print(f"⚠️ Ignorado: '{alertname}' ya está activa con mismo summary para {chat_id}")
            return

        if status == "firing":
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=5)
            if r.status_code == 200:
                message_id = r.json()["result"]["message_id"]
                save_message(alertname, chat_id, raw_summary, message_id, status)
                print(f"✅ Alerta enviada: {alertname} - {raw_summary}")
            else:
                print(f"❌ Error al enviar mensaje: {r.text}")

        elif status == "resolved" and message_id:
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML"
            }
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json=payload, timeout=5)
            if r.status_code == 200:
                save_message(alertname, chat_id, raw_summary, message_id, status)
                print(f"✅ Alerta resuelta: {alertname} - {raw_summary}")
            else:
                print(f"❌ Error al editar mensaje: {r.text}")
        else:
            print("⚠️ No se encontró mensaje para resolver.")

    except Exception as e:
        print(f"⚠️ Error al procesar alerta: {e}")

@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(force=True)
    alerts = data.get("alerts", [])

    if not alerts:
        return {"status": "no alerts"}

    for alert in alerts:
        threading.Thread(target=procesar_alerta, args=(alert,)).start()

    return {"status": "procesando en background"}

@app.route("/ping", methods=["GET", "HEAD"])
def ping():
    return "", 200

@app.route("/")
def home():
    return "✅ Bot de Telegram para Grafana está en funcionamiento."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
