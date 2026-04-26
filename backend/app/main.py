"""
FastAPI Application
"""

import json
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_engine
from app.models import Base

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if settings.telegram_bot_token and settings.telegram_webhook_url:
        from app.messaging.telegram import set_webhook

        set_webhook(f"{settings.telegram_webhook_url}/api/telegram/webhook")

    yield

    await async_engine.dispose()


app = FastAPI(
    title="AI Agent Orchestration Platform",
    description="Create, configure, and orchestrate AI agents into collaborative workflows.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes.agents import router as agents_router
from app.api.routes.workflows import router as workflows_router
from app.api.routes.executions import router as executions_router
from app.api.routes.messages import router as messages_router
from app.api.routes.telegram import router as telegram_router
from app.api.routes.tools import router as tools_router
from app.api.routes.templates import router as templates_router

app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(workflows_router, prefix="/api/workflows", tags=["Workflows"])
app.include_router(executions_router, prefix="/api/executions", tags=["Executions"])
app.include_router(messages_router, prefix="/api/messages", tags=["Messages"])
app.include_router(telegram_router, prefix="/api/telegram", tags=["Telegram"])
app.include_router(tools_router, prefix="/api/tools", tags=["Tools"])
app.include_router(templates_router, prefix="/api/templates", tags=["Templates"])


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, execution_id: str):
        await websocket.accept()
        self.active.setdefault(execution_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, execution_id: str):
        if execution_id in self.active:
            self.active[execution_id] = [
                ws for ws in self.active[execution_id] if ws != websocket
            ]

    async def broadcast(self, execution_id: str, message: dict):
        dead = []
        for ws in self.active.get(execution_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, execution_id)


manager = ConnectionManager()


@app.websocket("/ws/executions/{execution_id}")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    await manager.connect(websocket, execution_id)
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"execution:{execution_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for execution %s", execution_id)
    finally:
        await pubsub.unsubscribe(f"execution:{execution_id}")
        await redis.aclose()
        manager.disconnect(websocket, execution_id)


@app.websocket("/ws/agents/{agent_id}/telegram")
async def websocket_agent_telegram(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"agent:{agent_id}:telegram")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_json(json.loads(message["data"]))
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"agent:{agent_id}:telegram")
        await redis.aclose()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "AI Agent Orchestration Platform API", "docs": "/docs"}
