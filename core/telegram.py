import json
import re

import requests
from django.conf import settings

from .content_services import create_content_item_from_url
from .models import Channel, TelegramAccount


URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)


def extract_first_url(text):
    match = URL_RE.search(text or "")
    if not match:
        return ""
    return match.group(0).rstrip(".,;)")


def send_telegram_message(chat_id, text):
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=8,
        )
    except requests.RequestException:
        return


def message_from_update(update):
    return update.get("message") or update.get("edited_message") or {}


def sender_from_message(message):
    return message.get("from") or {}


def text_from_message(message):
    return message.get("text") or message.get("caption") or ""


def upsert_telegram_account(user, sender, chat_id):
    account, _ = TelegramAccount.objects.update_or_create(
        telegram_user_id=sender["id"],
        defaults={
            "user": user,
            "username": sender.get("username", ""),
            "first_name": sender.get("first_name", ""),
            "last_name": sender.get("last_name", ""),
            "chat_id": chat_id,
        },
    )
    return account


def connect_telegram_account(sender, chat_id, link_code):
    channel = Channel.objects.select_related("owner").filter(telegram_link_code=link_code).first()
    if not channel:
        send_telegram_message(chat_id, "Codi de vinculacio no valid. Copia el codi actual des de Selectora.")
        return {"action": "connect", "linked": False}

    upsert_telegram_account(channel.owner, sender, chat_id)
    send_telegram_message(chat_id, f"Telegram vinculat a Selectora. Les URLs es publicaran a: {channel.name}")
    return {"action": "connect", "linked": True, "user_id": channel.owner_id}


def publish_url_from_telegram(account, chat_id, url):
    item, created, error = create_content_item_from_url(account.user, url)
    if created:
        text = f"Publicat a Selectora: {item.title}"
        if error:
            text += "\nNo s'han pogut obtenir totes les metadades."
    else:
        text = f"Aquest contingut ja era al teu canal: {item.title}"
    send_telegram_message(chat_id, text)
    return {"action": "publish", "created": created, "item_id": item.pk, "error": error}


def process_telegram_update(raw_body):
    try:
        update = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"action": "ignored", "reason": "invalid_json"}

    message = message_from_update(update)
    sender = sender_from_message(message)
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = text_from_message(message).strip()
    if not message or not sender.get("id"):
        return {"action": "ignored", "reason": "no_message"}

    if text.startswith("/start"):
        send_telegram_message(
            chat_id,
            "Envia /connect CODI per vincular Telegram amb Selectora. Trobaras el codi a Configurar canal.",
        )
        return {"action": "start"}

    if text.startswith("/connect"):
        parts = text.split(maxsplit=1)
        link_code = parts[1].strip() if len(parts) > 1 else ""
        return connect_telegram_account(sender, chat_id, link_code)

    account = TelegramAccount.objects.select_related("user").filter(telegram_user_id=sender["id"]).first()
    if not account:
        send_telegram_message(chat_id, "Primer vincula aquest Telegram amb /connect CODI.")
        return {"action": "needs_connection"}

    if chat_id and account.chat_id != chat_id:
        account.chat_id = chat_id
        account.save(update_fields=["chat_id", "updated_at"])

    url = extract_first_url(text)
    if not url:
        send_telegram_message(chat_id, "Envia un missatge amb una URL per publicar-la al teu canal.")
        return {"action": "ignored", "reason": "no_url"}

    return publish_url_from_telegram(account, chat_id, url)
