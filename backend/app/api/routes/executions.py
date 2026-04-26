"""Execution routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import WorkflowExecution, ExecutionLog, Workflow, ExecutionStatus
from app.schemas import ExecutionCreate, ExecutionResponse

router = APIRouter()


@router.post("", response_model=ExecutionResponse, status_code=201)
async def create_execution(payload: ExecutionCreate, db: AsyncSession = Depends(get_db)):
    wf_result = await db.execute(select(Workflow).where(Workflow.id == payload.workflow_id))
    wf = wf_result.scalar_one_or_none()
    if not wf:
        raise HTTPException(404, "Workflow not found")

    execution = WorkflowExecution(
        workflow_id=payload.workflow_id,
        status=ExecutionStatus.pending,
        trigger=payload.trigger,
        input_data=payload.input_data,
    )
    db.add(execution)
    await db.flush()
    await db.refresh(execution)
    eid = execution.id

    # Commit before the Celery task: get_db() only commits after the handler returns.
    # The worker uses another DB connection and would not see an uncommitted row.
    await db.commit()

    from app.workers.tasks import execute_workflow
    execute_workflow.delay(eid)

    res = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == eid)
        .options(selectinload(WorkflowExecution.logs))
    )
    return res.scalar_one()


@router.get("", response_model=list[ExecutionResponse])
async def list_executions(
    workflow_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(WorkflowExecution).options(selectinload(WorkflowExecution.logs))
    if workflow_id:
        q = q.where(WorkflowExecution.workflow_id == workflow_id)
    result = await db.execute(q.order_by(WorkflowExecution.started_at.desc()).limit(50))
    return result.scalars().all()


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id)
        .options(selectinload(WorkflowExecution.logs))
    )
    exc = result.scalar_one_or_none()
    if not exc:
        raise HTTPException(404, "Execution not found")
    return exc


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    exc = result.scalar_one_or_none()
    if not exc:
        raise HTTPException(404, "Execution not found")

    if exc.celery_task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(exc.celery_task_id, terminate=True)

    exc.status = ExecutionStatus.cancelled
    await db.flush()
    return {"message": "Cancelled"}
