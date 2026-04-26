"""Sync persistence for inter-agent (A2A) tool messages (Celery / tool context)."""
from __future__ import annotations

import logging

from app.database import SyncSessionLocal
from app.models import Message, MessageRole

logger = logging.getLogger(__name__)


def record_a2a_message(
    execution_id: str,
    from_agent_id: str,
    to_agent_id: str,
    content: str,
) -> str | None:
    if not execution_id or not from_agent_id:
        return None
    session = SyncSessionLocal()
    try:
        m = Message(
            execution_id=execution_id,
            agent_id=from_agent_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            role=MessageRole.agent,
            content=content,
            channel="a2a",
            message_metadata={"to_agent_id": to_agent_id},
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        return m.id
    except Exception as e:
        logger.error("A2A persist failed: %s", e, exc_info=True)
        session.rollback()
        return None
    finally:
        session.close()
