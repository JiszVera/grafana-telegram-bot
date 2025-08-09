elif status == "resolved":
    message_id = message_store.get(alertname)
    if not message_id:
        print(f"Error: No se encontró message_id para la alerta {alertname}")
        return {"status": "no se encontró message_id para editar"}

    payload = {
        "chat_id": CHAT_IDs[0],  # Asumimos que editas el mensaje en el primer chat_id
        "message_id": message_id,
        "text": text,  # Este texto incluye el emoji verde 🟢
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

















