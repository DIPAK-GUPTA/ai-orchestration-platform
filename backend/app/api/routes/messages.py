"""Messages route"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Message
from app.schemas import MessageResponse

router = APIRouter()


@router.get("", response_model=list[MessageResponse])
async def list_messages(
    execution_id: str | None = None,
    agent_id: str | None = None,
    channel: str | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(Message)
    if execution_id:
        q = q.where(Message.execution_id == execution_id)
    if agent_id:
        q = q.where(Message.agent_id == agent_id)
    if channel:
        q = q.where(Message.channel == channel)
    result = await db.execute(q.order_by(Message.created_at.desc()).limit(limit))
    return list(reversed(result.scalars().all()))  # chronological
