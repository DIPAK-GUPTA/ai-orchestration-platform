"""
Agent Memory
------------
Provides buffer and summary memory for agents.
Persists to Redis (fast) with optional PostgreSQL backup.

Uses the synchronous ``redis`` client. Async ``redis`` connections (``redis.asyncio``)
must be closed before ``asyncio.run()`` tears down the event loop; the Celery worker
uses ``asyncio.run()`` for workflows, and GC on unclosed async clients otherwise logs
"Event loop is closed" during connection ``__del__``.
"""

import asyncio
import json
import logging
from typing import Optional

import redis
from app.config import settings

logger = logging.getLogger(__name__)


class AgentMemory:
    """Pluggable memory for agents. Defaults to buffer memory stored in Redis."""

    def __init__(self, agent_id: str, config: dict):
        self.agent_id = agent_id
        self.memory_type = config.get("type", "buffer")
        self.max_tokens = config.get("max_tokens", 4096)
        self.persist = config.get("persist", True)
        self._redis: Optional[redis.Redis] = None

    def _get_redis(self) -> redis.Redis:
        if not self._redis:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    @property
    def _key(self) -> str:
        return f"agent_memory:{self.agent_id}"

    def _load_sync(self) -> str:
        if not self.persist:
            return ""
        try:
            r = self._get_redis()
            raw = r.get(self._key)
            if raw:
                data = json.loads(raw)
                entries = data.get("entries", [])
                return "\n".join(entries[-20:])
            return ""
        except Exception as e:
            logger.warning("Memory load error for %s: %s", self.agent_id, e)
            return ""

    async def load(self) -> str:
        return await asyncio.to_thread(self._load_sync)

    def _save_sync(self, content: str) -> None:
        if not self.persist:
            return
        try:
            r = self._get_redis()
            raw = r.get(self._key)
            if raw:
                data = json.loads(raw)
            else:
                data = {"entries": [], "agent_id": self.agent_id}

            data["entries"].append(content)
            data["entries"] = data["entries"][-100:]

            r.setex(self._key, 86400 * 7, json.dumps(data))
        except Exception as e:
            logger.warning("Memory save error for %s: %s", self.agent_id, e)

    async def save(self, content: str) -> None:
        await asyncio.to_thread(self._save_sync, content)

    def _clear_sync(self) -> None:
        try:
            r = self._get_redis()
            r.delete(self._key)
        except Exception as e:
            logger.warning("Memory clear error for %s: %s", self.agent_id, e)

    async def clear(self) -> None:
        await asyncio.to_thread(self._clear_sync)

    def _get_all_sync(self) -> list[str]:
        try:
            r = self._get_redis()
            raw = r.get(self._key)
            if raw:
                data = json.loads(raw)
                return data.get("entries", [])
            return []
        except Exception:
            return []

    async def get_all(self) -> list[str]:
        return await asyncio.to_thread(self._get_all_sync)
