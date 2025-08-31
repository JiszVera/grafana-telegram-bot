from flask import Flask, request
import requests
import os
from supabase import create_client, Client
import logging

app = Flask(__name__)

# Configura el log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if not BOT_TOKEN:
    raise ValueError("Falta BOT_TOKEN en las variables de entorno.")

# Mapea las zonas a sus chat_id correspondientes
ZONA_CHAT_IDS = {
    "Norte": os.environ.get("CHAT_ID_NORTE"),
    "Sur": os.environ.get("CHAT_ID_SUR"),
}

# Guardar el mensaje en Supabase (insertar o actualizar)
def save_message(alertname, chat_id, message_id, status):
    data = supabase.table("alerts").select("*").eq("alertname", alertname).eq("chat_id", chat_id).execute()
    if data.data:
        supabase.table("alerts").update({
            "message_id": message_id,
            "status": status
        }).eq("alertname", alertname).eq("chat_id", chat_id).execute()
    else:
        supabase.table("alerts").insert({
            "alertname": alertname,
            "chat_id": chat_id,
            "message_id": message_id,
            "status": status
        }).execute()

# Obtener el estado previo de la alerta
def get_alert_status(alertname, chat_id):
    data = supabase.table("alerts").select("status, message_id").eq("alertname", alertname).eq("chat_id", chat_id).execute()
    if data.data:
        return data.data[0]["status"], data.data[0]["message_id"]
    return None, None

# Procesar alerta individual
def procesar_alerta(alert):
    try:
        status = alert.get("status")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alertname = labels.get("alertname", "Sin nombre")
        summary = annotations.get("summary", "🚨GRUPO EN SERVICIO🚨")
        zona = labels.get("Zona")
        chat_id = ZONA_CHAT_IDS.get(zona)

        if not chat_id:
            logger.warning(f"⚠️ No hay chat_id configurado para la zona '{zona}'")
            return

        if status == "firing":
            emoji = "🔴"
            title = "ALERTA ACTIVA"
        elif status == "resolved":
            emoji = "🟢"
            title = "ALERTA RESUELTA"
        else:
            logger.warning(f"⚠️ Estado desconocido para alerta: {status}")
            return

        text = f"{emoji} <b>{title}</b>\n\n{alertname}\n\n{summary}\n"

        # Consulta si ya existe esa alerta
        prev_status, message_id = get_alert_status(alertname, chat_id)

        # Lógica principal
        if status == "firing":
            if prev_status == "firing":
                logger.info(f"🔁 Alerta '{alertname}' ya fue enviada y sigue activa. Ignorada.")
                return
            else:
                # Enviar nueva alerta
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
                r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=5)
                if r.status_code == 200:
                    message_id = r.json()["result"]["message_id"]
                    save_message(alertname, chat_id, message_id, status)
                    logger.info(f"✅ Alerta '{alertname}' enviada a zona '{zona}'")
                else:
                    logger.error(f"❌ Error al enviar mensaje: {r.text}")

        elif status == "resolved":
            if message_id:
                # Editar mensaje existente
                payload = {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
                r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json=payload, timeout=5)
                if r.status_code == 200:
                    save_message(alertname, chat_id, message_id, status)
                    logger.info(f"✅ Alerta '{alertname}' resuelta y actualizada en zona '{zona}'")
                else:
                    logger.error(f"❌ Error al editar mensaje: {r.text}")
            else:
                logger.warning(f"ℹ️ Se resolvió '{alertname}' pero no hay mensaje previo para editar.")

    except Exception as e:
        logger.error(f"⚠️ Error al procesar alerta: {e}")

# Endpoint principal para recibir alertas
@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(force=True)
    alerts = data.get("alerts", [])

    if not alerts:
        return {"status": "no alerts"}

    for alert in alerts:
        procesar_alerta(alert)

    return {"status": "procesando"}

# Verificación de salud
@app.route("/ping", methods=["GET", "HEAD"])
def ping():
    return "", 200

# Página principal
@app.route("/")
def home():
    return "✅ Bot de Telegram para Grafana está en funcionamiento."

# Iniciar servidor Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
