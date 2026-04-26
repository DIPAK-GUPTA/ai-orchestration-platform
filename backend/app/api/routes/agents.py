from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sqldelete
from typing import Optional

from app.database import get_db
from app.models import Agent
from app.schemas import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Agent)
    if status:
        q = q.where(Agent.status == status)
    result = await db.execute(q.order_by(Agent.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
):
    agent = Agent(
        name=payload.name,
        role=payload.role,
        system_prompt=payload.system_prompt,
        model=payload.model,
        tools=payload.tools,
        skills=payload.skills,
        memory_config=payload.memory_config.model_dump(),
        guardrails=payload.guardrails.model_dump(),
        schedule=payload.schedule.model_dump() if payload.schedule else None,
        interaction_rules=payload.interaction_rules,
        channel_config=payload.channel_config,
        is_telegram_agent=payload.is_telegram_agent,
        telegram_chat_id=payload.telegram_chat_id,
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "memory_config" and value is not None:
            value = value if isinstance(value, dict) else value.model_dump()
        elif key == "guardrails" and value is not None:
            value = value if isinstance(value, dict) else value.model_dump()
        elif key == "schedule" and value is not None:
            value = value if isinstance(value, dict) else value.model_dump()
        setattr(agent, key, value)

    await db.flush()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.execute(sqldelete(Agent).where(Agent.id == agent_id))


@router.post("/{agent_id}/memory/clear")
async def clear_agent_memory(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    from app.agents.memory import AgentMemory
    mem = AgentMemory(agent_id, agent.memory_config or {})
    await mem.clear()
    return {"message": "Memory cleared"}


@router.get("/{agent_id}/memory")
async def get_agent_memory(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    from app.agents.memory import AgentMemory
    mem = AgentMemory(agent_id, agent.memory_config or {})
    entries = await mem.get_all()
    return {"entries": entries, "count": len(entries)}
