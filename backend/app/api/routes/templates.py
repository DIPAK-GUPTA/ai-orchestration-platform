"""Workflow templates route"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import (
    Agent,
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowStatus,
)
from app.schemas import WorkflowResponse
from app.agents.templates import get_all_templates, get_template

router = APIRouter()


@router.get("")
async def list_templates():
    return get_all_templates()


@router.get("/{template_id}")
async def get_template_detail(template_id: str):
    t = get_template(template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@router.post("/{template_id}/instantiate", response_model=WorkflowResponse)
async def instantiate_template(
    template_id: str,
    name: str = "From template",
    db: AsyncSession = Depends(get_db),
):
    t = get_template(template_id)
    if not t:
        raise HTTPException(404, "Template not found")

    slot_to_agent: dict[str, str] = {}
    for adef in t["agents"]:
        slot = adef["slot"]
        agent = Agent(
            name=adef.get("name", "Agent"),
            role=adef.get("role", "Assistant"),
            system_prompt=adef["system_prompt"],
            model=adef.get("model", "gpt-4o-mini"),
            tools=adef.get("tools", []),
            skills=adef.get("skills", []),
            is_telegram_agent=adef.get("is_telegram_agent", False),
        )
        db.add(agent)
        await db.flush()
        slot_to_agent[slot] = agent.id

    # New UUID per node — template ids like "start"/"end" are global-unique in DB, not per-workflow.
    id_map: dict[str, str] = {n["id"]: str(uuid.uuid4()) for n in t["graph"]["nodes"] if n.get("id")}

    remapped_nodes = []
    for n in t["graph"]["nodes"]:
        oid = n.get("id")
        if not oid:
            continue
        entry = {**n, "id": id_map[oid]}
        remapped_nodes.append(entry)
    remapped_edges = [
        {
            **e,
            "source_node_id": id_map.get(e["source_node_id"], e["source_node_id"]),
            "target_node_id": id_map.get(e["target_node_id"], e["target_node_id"]),
        }
        for e in t["graph"]["edges"]
    ]
    new_positions: dict = {}
    for n in t["graph"]["nodes"]:
        oid = n.get("id")
        if not oid or oid not in id_map:
            continue
        pos = n.get("position") or {}
        new_positions[id_map[oid]] = pos if isinstance(pos, dict) else {}

    wf = Workflow(
        name=name,
        description=t.get("description", ""),
        status=WorkflowStatus.draft,
        template_id=template_id,
        graph_definition={"nodes": remapped_nodes, "edges": remapped_edges},
        node_positions=new_positions,
    )
    db.add(wf)
    await db.flush()

    for n in t["graph"]["nodes"]:
        if n.get("node_type") == "agent" and n.get("agent_slot"):
            aid = slot_to_agent.get(n["agent_slot"])
        else:
            aid = n.get("agent_id")
        pos = n.get("position") or {}
        old_id = n.get("id")
        if not old_id or old_id not in id_map:
            continue
        node = WorkflowNode(
            id=id_map[old_id],
            workflow_id=wf.id,
            agent_id=aid,
            node_type=n.get("node_type", "agent"),
            label=n.get("label", ""),
            config=n.get("config", {}),
            position_x=pos.get("x", 0) if isinstance(pos, dict) else 0.0,
            position_y=pos.get("y", 0) if isinstance(pos, dict) else 0.0,
        )
        db.add(node)

    for e in t["graph"]["edges"]:
        src = id_map.get(e["source_node_id"], e["source_node_id"])
        tgt = id_map.get(e["target_node_id"], e["target_node_id"])
        edge = WorkflowEdge(
            id=str(uuid.uuid4()),
            workflow_id=wf.id,
            source_node_id=src,
            target_node_id=tgt,
            condition=e.get("condition"),
            label=e.get("label", ""),
        )
        db.add(edge)

    await db.flush()
    from sqlalchemy.orm import selectinload
    r = await db.execute(
        select(Workflow)
        .where(Workflow.id == wf.id)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
    )
    return r.scalar_one()
