"""
Telegram integration (HTTP API, webhook)
"""

import json
import logging
import httpx
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def send_telegram_message(chat_id: str, text: str, parse_mode: str = "") -> bool:
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping send")
        return False

    try:
        base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        j: dict = {"chat_id": chat_id, "text": text}
        if parse_mode:
            j["parse_mode"] = parse_mode
        response = httpx.post(
            f"{base}/sendMessage",
            json=j,
            timeout=10.0,
        )
        data = response.json()
        if not data.get("ok"):
            logger.error("Telegram send failed: %s", data)
            return False
        return True
    except Exception as e:
        logger.error("Telegram send error: %s", e)
        return False


def set_webhook(webhook_url: str) -> bool:
    if not settings.telegram_bot_token:
        return False
    try:
        base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        response = httpx.post(f"{base}/setWebhook", json={"url": webhook_url}, timeout=10.0)
        data = response.json()
        logger.info("Webhook set: %s", data)
        return data.get("ok", False)
    except Exception as e:
        logger.error("Webhook set error: %s", e)
        return False


def delete_webhook() -> bool:
    if not settings.telegram_bot_token:
        return False
    try:
        base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        response = httpx.post(f"{base}/deleteWebhook", timeout=10.0)
        return response.json().get("ok", False)
    except Exception:
        return False


def get_bot_info() -> Optional[dict]:
    if not settings.telegram_bot_token:
        return None
    try:
        base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        response = httpx.get(f"{base}/getMe", timeout=10.0)
        data = response.json()
        if data.get("ok"):
            return data["result"]
        return None
    except Exception:
        return None


async def handle_telegram_update(update: dict, db) -> None:
    from app.models import Agent, AgentStatus
    from sqlalchemy import select

    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")
    if not text:
        return

    result = await db.execute(
        select(Agent)
        .where(Agent.is_telegram_agent.is_(True), Agent.status == AgentStatus.active)
        .order_by(Agent.created_at)
    )
    agents = list(result.scalars().all())
    if not agents:
        send_telegram_message(
            chat_id, "No agents are configured for Telegram. Enable *Telegram* on an agent in the web UI."
        )
        return

    target = next((a for a in agents if a.telegram_chat_id == chat_id), agents[0])
    if not target.telegram_chat_id:
        target.telegram_chat_id = chat_id
        await db.flush()
        send_telegram_message(
            chat_id, f"Linked to *{target.name}* ({target.role}). Send your message to continue."
        )

    from app.workers.tasks import process_telegram_message
    process_telegram_message.delay(chat_id, text, target.id)
