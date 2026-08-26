"""Workflow management API routes with DAG execution."""

from datetime import UTC, datetime


def _utcnow() -> datetime:
    """Naive UTC datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(UTC).replace(tzinfo=None)
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import (
    Workflow, WorkflowExecution, Job, JobStatus, WorkflowStatus,
    ScheduleType
)
from app.schemas.schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowExecutionResponse
)
from app.core.auth import get_current_user
from app.core.redis_client import JobQueue

router = APIRouter(prefix="/workflows", tags=["workflows"])


def validate_dag(tasks: list) -> dict:
    """Validate that the task graph is a valid DAG (no cycles)."""
    task_ids = {t.id for t in tasks}
    in_degree = {t.id: 0 for t in tasks}
    adj = {t.id: [] for t in tasks}
    
    for t in tasks:
        for dep in t.depends_on:
            if dep not in task_ids:
                raise ValueError(f"Task '{t.id}' depends on unknown task '{dep}'")
            adj[dep].append(t.id)
            in_degree[t.id] += 1
    
    # Topological sort (Kahn's algorithm)
    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    sorted_order = []
    while queue:
        node = queue.pop(0)
        sorted_order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(sorted_order) != len(task_ids):
        raise ValueError("Workflow contains a cycle")
    
    return {"tasks": {t.id: {"depends_on": t.depends_on, "name": t.name} for t in tasks}}


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workflow).order_by(Workflow.created_at.desc()))
    return result.scalars().all()


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    wf_data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    dag = validate_dag(wf_data.tasks)
    
    workflow = Workflow(
        name=wf_data.name,
        description=wf_data.description,
        dag_definition={
            "tasks": {
                t.id: {
                    "command": t.command,
                    "depends_on": t.depends_on,
                    "payload": t.payload,
                    "max_retries": t.max_retries,
                    "timeout_seconds": t.timeout_seconds,
                    "name": t.name,
                }
                for t in wf_data.tasks
            }
        },
        schedule_type=wf_data.schedule_type,
        cron_expression=wf_data.cron_expression,
        interval_seconds=wf_data.interval_seconds,
        owner_id=user.id,
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    wf_data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if wf_data.name is not None:
        wf.name = wf_data.name
    if wf_data.description is not None:
        wf.description = wf_data.description
    if wf_data.tasks is not None:
        dag = validate_dag(wf_data.tasks)
        wf.dag_definition = {
            "tasks": {
                t.id: {
                    "command": t.command,
                    "depends_on": t.depends_on,
                    "payload": t.payload,
                    "max_retries": t.max_retries,
                    "timeout_seconds": t.timeout_seconds,
                    "name": t.name,
                }
                for t in wf_data.tasks
            }
        }
    wf.updated_at = _utcnow()
    await db.commit()
    await db.refresh(wf)
    return wf


@router.post("/{workflow_id}/run", response_model=WorkflowExecutionResponse)
async def run_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Execute a workflow by creating jobs for each task and enqueueing ready tasks."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Create execution record
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        status=WorkflowStatus.RUNNING,
        task_states={},
        started_at=_utcnow(),
    )
    db.add(execution)
    await db.flush()
    
    tasks = wf.dag_definition.get("tasks", {})
    task_jobs = {}
    
    # Create a Job for each task
    for task_id, task_def in tasks.items():
        job = Job(
            name=f"{wf.name} / {task_def.get('name', task_id)}",
            command=task_def["command"],
            payload={
                **task_def.get("payload", {}),
                "_workflow_id": str(workflow_id),
                "_execution_id": str(execution.id),
                "_task_id": task_id,
            },
            workflow_id=workflow_id,
            max_retries=task_def.get("max_retries", 3),
            timeout_seconds=task_def.get("timeout_seconds", 300),
            status=JobStatus.PENDING,
        )
        db.add(job)
        await db.flush()
        task_jobs[task_id] = job
        execution.task_states[task_id] = {"status": "pending", "job_id": str(job.id)}
    
    # Enqueue tasks with no dependencies (roots)
    for task_id, task_def in tasks.items():
        if not task_def.get("depends_on"):
            job = task_jobs[task_id]
            job.status = JobStatus.QUEUED
            queue = JobQueue()
            await queue.enqueue(str(job.id))
            execution.task_states[task_id]["status"] = "queued"
    
    await db.commit()
    await db.refresh(execution)
    return execution


@router.get("/{workflow_id}/executions", response_model=list[WorkflowExecutionResponse])
async def list_executions(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .order_by(WorkflowExecution.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.delete(wf)
    await db.commit()
