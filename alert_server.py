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

    # Si es firing, enviamos nuevo mensaje y guardamos message_id
    if status == "firing":
        # Verificamos si ya se envió el mensaje previamente
        if alertname in message_store:
            return {"status": "alerta ya enviada", "message_id": message_store[alertname]}

        payload = {
            "text": text,
            "parse_mode": "HTML"
        }

        # Enviar mensaje a todos los chat_ids y guardar el message_id
        for chat_id in CHAT_IDs:
            payload["chat_id"] = chat_id
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(send_url, json=payload)

            if r.status_code == 200:
                resp = r.json()
                message_id = resp["result"]["message_id"]
                message_store[alertname] = message_id  # Guardamos el message_id
                print(f"Alerta enviada: {alertname} con message_id: {message_id}")
            else:
                return {"status": "error al enviar", "detail": r.text}, 500

        return {"status": "alertas enviadas"}

    # Si es resolved, editamos mensaje anterior (si existe)
    elif status == "resolved":
        message_id = message_store.get(alertname)
        if not message_id:
            print(f"Error: No se encontró message_id para la alerta {alertname}")
            return {"status": "no se encontró message_id para editar"}

        payload = {
            "chat_id": CHAT_IDs[0],  # Asumimos que editas el mensaje en el primer chat_id
            "message_id": message_id,
            "text": text,  # Editamos el mensaje con el emoji verde
            "parse_mode": "HTML"
        }

        edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        r = requests.post(edit_url, json=payload)

        if r.status_code == 200:
            print(f"Mensaje editado correctamente para {alertname}, message_id: {message_id}")
            return {"status": "mensaje editado"}
        else:
            print(f"Error al editar mensaje para {alertname}: {r.text}")
            return {"status": "error al editar", "detail": r.text}, 500




















