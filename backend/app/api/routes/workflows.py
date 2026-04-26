from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sqldelete
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Workflow, WorkflowNode, WorkflowEdge, WorkflowStatus
from app.schemas import WorkflowCreate, WorkflowUpdate, WorkflowResponse

router = APIRouter()


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .order_by(Workflow.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
):
    import uuid

    workflow = Workflow(
        name=payload.name,
        description=payload.description,
        template_id=payload.template_id,
        graph_definition=payload.graph_definition,
        node_positions=payload.node_positions,
        status=WorkflowStatus.draft,
    )
    db.add(workflow)
    await db.flush()

    for n in payload.nodes:
        node = WorkflowNode(
            id=n.id or str(uuid.uuid4()),
            workflow_id=workflow.id,
            agent_id=n.agent_id,
            node_type=n.node_type,
            label=n.label,
            config=n.config,
            position_x=n.position.x if n.position else 0.0,
            position_y=n.position.y if n.position else 0.0,
        )
        db.add(node)

    for e in payload.edges:
        edge = WorkflowEdge(
            id=e.id or str(uuid.uuid4()),
            workflow_id=workflow.id,
            source_node_id=e.source_node_id,
            target_node_id=e.target_node_id,
            condition=e.condition,
            label=e.label,
        )
        db.add(edge)

    await db.flush()
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow.id)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
    )
    return result.scalar_one()


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
):
    import uuid

    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "nodes" in update_data:
        for node in wf.nodes:
            await db.execute(
                sqldelete(WorkflowNode).where(WorkflowNode.id == node.id)
            )
        for n in payload.nodes:
            node = WorkflowNode(
                id=n.id or str(uuid.uuid4()),
                workflow_id=wf.id,
                agent_id=n.agent_id,
                node_type=n.node_type,
                label=n.label,
                config=n.config,
                position_x=n.position.x if n.position else 0.0,
                position_y=n.position.y if n.position else 0.0,
            )
            db.add(node)
        del update_data["nodes"]

    if "edges" in update_data:
        for edge in wf.edges:
            await db.execute(
                sqldelete(WorkflowEdge).where(WorkflowEdge.id == edge.id)
            )
        for e in payload.edges:
            edge = WorkflowEdge(
                id=e.id or str(uuid.uuid4()),
                workflow_id=wf.id,
                source_node_id=e.source_node_id,
                target_node_id=e.target_node_id,
                condition=e.condition,
                label=e.label,
            )
            db.add(edge)
        del update_data["edges"]

    for key, value in update_data.items():
        setattr(wf, key, value)

    await db.flush()
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == wf.id)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
    )
    return result.scalar_one()


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.execute(sqldelete(Workflow).where(Workflow.id == workflow_id))
