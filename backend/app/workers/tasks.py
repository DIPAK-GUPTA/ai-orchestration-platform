import asyncio
import json
import logging
from datetime import datetime

import redis as sync_redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.workers.celery_app import celery_app
from app.config import settings
from app.models import (
    Agent,
    Workflow,
    WorkflowExecution,
    ExecutionLog,
    ExecutionStatus,
    Message,
    MessageRole,
    AgentStatus,
)

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
redis_client = sync_redis.from_url(settings.redis_url, decode_responses=True)


def get_db() -> Session:
    return SessionLocal()


def publish_event(channel: str, event: dict) -> None:
    try:
        redis_client.publish(channel, json.dumps(event))
    except Exception as e:
        logger.warning("Failed to publish event: %s", e)


def create_log(
    db: Session,
    execution_id: str,
    agent_id: str | None,
    event: str,
    message: str,
    level: str = "info",
    data: dict | None = None,
    tokens_used: int = 0,
    cost_usd: float = 0.0,
) -> None:
    log = ExecutionLog(
        execution_id=execution_id,
        agent_id=agent_id,
        event=event,
        message=message,
        level=level,
        data=data or {},
        tokens_used=tokens_used,
        cost_usd=cost_usd,
    )
    db.add(log)
    db.commit()
    try:
        db.refresh(log)
        created = log.created_at.isoformat() if log.created_at else None
    except Exception:
        created = None
    log_id = getattr(log, "id", None)
    publish_event(
        f"execution:{execution_id}",
        {
            "type": "log",
            "log": {
                "id": log_id,
                "execution_id": execution_id,
                "agent_id": agent_id,
                "event": event,
                "message": message,
                "level": level,
                "data": data or {},
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "created_at": created,
            },
        },
    )


@celery_app.task(bind=True, name="app.workers.tasks.execute_workflow", max_retries=2)
def execute_workflow(self, execution_id: str) -> dict:
    db = get_db()
    try:
        execution: WorkflowExecution | None = (
            db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        )
        if not execution:
            raise ValueError("Execution not found: " + execution_id)

        execution.status = ExecutionStatus.running
        execution.celery_task_id = self.request.id
        db.commit()

        publish_event(
            f"execution:{execution_id}",
            {"type": "status_change", "status": "running", "execution_id": execution_id},
        )

        workflow: Workflow | None = (
            db.query(Workflow).filter(Workflow.id == execution.workflow_id).first()
        )
        if not workflow:
            raise ValueError("Workflow not found: " + execution.workflow_id)

        agent_configs: list[dict] = []
        for node in workflow.nodes:
            if not node.agent_id:
                continue
            agent = db.query(Agent).filter(Agent.id == node.agent_id).first()
            if agent:
                agent_configs.append(
                    {
                        "id": agent.id,
                        "name": agent.name,
                        "role": agent.role,
                        "system_prompt": agent.system_prompt,
                        "model": agent.model,
                        "tools": agent.tools or [],
                        "skills": agent.skills or [],
                        "memory_config": agent.memory_config or {},
                        "guardrails": agent.guardrails or {},
                        "interaction_rules": agent.interaction_rules or {},
                    }
                )

        graph_config = {
            "nodes": [
                {
                    "id": n.id,
                    "node_type": n.node_type,
                    "agent_id": n.agent_id,
                    "label": n.label,
                    "config": n.config or {},
                }
                for n in workflow.nodes
            ],
            "edges": [
                {
                    "source_node_id": e.source_node_id,
                    "target_node_id": e.target_node_id,
                    "condition": e.condition,
                    "label": e.label,
                }
                for e in workflow.edges
            ],
        }

        create_log(
            db,
            execution_id,
            None,
            "workflow_start",
            f"Starting workflow «{workflow.name}» with {len(agent_configs)} agent(s).",
        )

        def log_callback_sync(**kwargs):
            create_log(db, **kwargs)

        result = asyncio.run(
            _run_graph_async(
                graph_config=graph_config,
                agent_configs=agent_configs,
                execution_id=execution_id,
                workflow_id=workflow.id,
                input_data=execution.input_data,
                log_callback_sync=log_callback_sync,
            )
        )

        total_tokens = sum((result.get("token_usage") or {}).values())
        from app.agents.runtime import _estimate_cost

        tusage = result.get("token_usage") or {}
        amap = {a["id"]: a.get("model", "gpt-4o-mini") for a in agent_configs}
        total_cost = sum(
            _estimate_cost(amap.get(aid, "gpt-4o-mini"), int(tk)) for aid, tk in tusage.items()
        )
        execution.status = ExecutionStatus.completed
        execution.output_data = result.get("output", {}) or {}
        execution.completed_at = datetime.utcnow()
        execution.total_tokens = int(total_tokens)
        execution.total_cost_usd = float(total_cost)
        db.commit()

        for content in result.get("messages", []) or []:
            m = Message(
                execution_id=execution_id,
                role=MessageRole.assistant,
                content=str(content),
                channel="internal",
                message_metadata={},
            )
            db.add(m)
        db.commit()

        create_log(
            db,
            execution_id,
            None,
            "workflow_complete",
            f"Workflow completed. ~{int(total_tokens)} total token(s).",
        )

        publish_event(
            f"execution:{execution_id}",
            {
                "type": "status_change",
                "status": "completed",
                "execution_id": execution_id,
                "output": result.get("output", {}),
            },
        )
        return {"status": "completed", "execution_id": execution_id}

    except Exception as e:
        logger.error("Execution %s failed: %s", execution_id, e, exc_info=True)
        try:
            ex = (
                db.query(WorkflowExecution)
                .filter(WorkflowExecution.id == execution_id)
                .first()
            )
            if ex:
                ex.status = ExecutionStatus.failed
                ex.error = str(e)
                ex.completed_at = datetime.utcnow()
                db.commit()
            publish_event(
                f"execution:{execution_id}",
                {
                    "type": "status_change",
                    "status": "failed",
                    "execution_id": execution_id,
                    "error": str(e),
                },
            )
        except Exception:
            pass
        raise
    finally:
        db.close()


async def _run_graph_async(
    graph_config: dict,
    agent_configs: list[dict],
    execution_id: str,
    workflow_id: str,
    input_data: dict,
    log_callback_sync,
) -> dict:
    from app.agents.runtime import WorkflowGraph

    async def log_callback(**kwargs):
        log_callback_sync(**kwargs)

    graph = WorkflowGraph(
        workflow_config=graph_config,
        agents=agent_configs,
        log_callback=log_callback,
    ).build()
    return await graph.run(
        execution_id=execution_id,
        workflow_id=workflow_id,
        input_data=input_data,
    )


@celery_app.task(name="app.workers.tasks.process_telegram_message")
def process_telegram_message(chat_id: str, user_message: str, agent_id: str) -> dict:
    from app.messaging.telegram import send_telegram_message

    db = get_db()
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            send_telegram_message(chat_id, "Agent not found.")
            return {"status": "error", "reason": "agent_not_found"}

        incoming = Message(
            agent_id=agent_id,
            role=MessageRole.user,
            content=user_message,
            channel="telegram",
            channel_message_id=chat_id,
            message_metadata={},
        )
        db.add(incoming)
        db.commit()

        result = asyncio.run(_run_single_agent(agent, user_message))
        response_text = (result or {}).get("content", "I'm processing your request.")

        out = Message(
            agent_id=agent_id,
            role=MessageRole.assistant,
            content=response_text,
            channel="telegram",
            channel_message_id=chat_id,
            message_metadata={},
        )
        db.add(out)
        db.commit()

        send_telegram_message(chat_id, response_text, parse_mode="")
        publish_event(
            f"agent:{agent_id}:telegram",
            {
                "type": "telegram_message",
                "chat_id": chat_id,
                "user_message": user_message,
                "agent_response": response_text,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        return {"status": "ok", "response": response_text}

    except Exception as e:
        logger.error("Telegram process error: %s", e, exc_info=True)
        send_telegram_message(str(chat_id), "Sorry, something went wrong. Try again later.")
        return {"status": "error", "reason": str(e)}
    finally:
        db.close()


async def _run_single_agent(agent, user_message: str) -> dict:
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.agents.runtime import _build_llm
    from app.agents.memory import AgentMemory

    llm = _build_llm(agent.model)
    # Tool execution for external Telegram is kept simple (full tool loop lives in LangGraph workflow runs).
    llm_use = llm
    mem = AgentMemory(agent.id, agent.memory_config or {})
    ctx = await mem.load()
    parts = [SystemMessage(content=agent.system_prompt)]
    if (agent.skills or []):
        parts.append(
            SystemMessage(
                content="Skills: " + ", ".join(agent.skills or [])
            )
        )
    if ctx:
        parts.append(SystemMessage(content="Memory context:\n" + ctx))
    parts.append(HumanMessage(content=user_message))
    response = await llm_use.ainvoke(parts)
    if getattr(response, "tool_calls", None):
        # If the model still requests tools, re-ask for a plain text reply
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke(
            parts
            + [response, HumanMessage(content="Reply with a helpful plain-text answer only; do not use tools.")]
        )
    content = (response.content or "").strip() or " "
    await mem.save(f"User: {user_message!s}\nAssistant: {content[:500]}")
    return {"content": content}


@celery_app.task(name="app.workers.tasks.check_scheduled_agents")
def check_scheduled_agents() -> None:
    try:
        from croniter import croniter
    except ImportError:
        logger.warning("croniter not installed; scheduled agents disabled")
        return
    db = get_db()
    try:
        agents = db.query(Agent).filter(Agent.status == AgentStatus.active).all()
        now = datetime.utcnow()
        for agent in agents:
            schedule = agent.schedule or {}
            if not schedule.get("enabled") or not schedule.get("cron"):
                continue
            try:
                cron = croniter(schedule["cron"], now)
                prev = cron.get_prev(datetime)
                if (now - prev).total_seconds() < 60:
                    p = (schedule or {}).get("trigger_prompt", "Run your scheduled task now.")
                    if agent.telegram_chat_id and agent.is_telegram_agent:
                        process_telegram_message.delay(
                            str(agent.telegram_chat_id), p, str(agent.id)
                        )
            except Exception as e:
                logger.warning("Schedule check: %s — %s", agent.name, e)
    finally:
        db.close()
