"""Telegram webhook endpoint"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.messaging.telegram import get_bot_info, set_webhook, delete_webhook

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.telegram_bot_token:
        raise HTTPException(400, "Telegram not configured")

    update = await request.json()
    from app.messaging.telegram import handle_telegram_update
    await handle_telegram_update(update, db)
    return {"ok": True}


@router.get("/bot-info")
async def bot_info():
    info = get_bot_info()
    if not info:
        return {"connected": False, "reason": "Bot token not set or invalid"}
    return {"connected": True, "bot": info}


@router.post("/webhook/register")
async def register_webhook(url: str):
    success = set_webhook(f"{url.rstrip('/')}/api/telegram/webhook")
    return {"success": success, "url": f"{url.rstrip('/')}/api/telegram/webhook"}


@router.post("/webhook/delete")
async def remove_webhook():
    success = delete_webhook()
    return {"success": success}
