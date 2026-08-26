"""Worker monitoring and management API routes."""

from datetime import UTC, datetime


def _utcnow() -> datetime:
    """Naive UTC datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(UTC).replace(tzinfo=None)
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import Worker, Job, JobStatus, JobLog
from app.schemas.schemas import WorkerResponse, DashboardStats, LogEntry
from app.core.redis_client import JobQueue

router = APIRouter(tags=["workers"])


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    now = _utcnow()
    
    total = (await db.execute(select(func.count(Job.id)))).scalar()
    running = (await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.RUNNING)
    )).scalar()
    queued = (await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.QUEUED)
    )).scalar()
    failed = (await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.FAILED)
    )).scalar()
    completed = (await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.SUCCESS)
    )).scalar()
    
    from app.models.models import Workflow
    workflows = (await db.execute(select(func.count(Workflow.id)))).scalar()
    
    active_workers = (await db.execute(
        select(func.count(Worker.id)).where(Worker.status == "active")
    )).scalar()
    
    from datetime import timedelta
    yesterday = now - timedelta(hours=24)
    recent = (await db.execute(
        select(func.count(Job.id)).where(Job.created_at >= yesterday)
    )).scalar()
    
    return DashboardStats(
        total_jobs=total,
        running_jobs=running,
        queued_jobs=queued,
        failed_jobs=failed,
        completed_jobs=completed,
        total_workflows=workflows,
        active_workers=active_workers,
        jobs_last_24h=recent,
    )


@router.get("/workers", response_model=list[WorkerResponse])
async def list_workers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Worker).order_by(Worker.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/jobs/{job_id}/logs", response_model=list[LogEntry])
async def get_job_logs(
    job_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID
    result = await db.execute(
        select(JobLog)
        .where(JobLog.job_id == UUID(job_id))
        .order_by(JobLog.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.delete("/workers/{worker_id}")
async def delete_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a stopped worker record."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Worker not found")
    await db.delete(worker)
    await db.commit()
    return {"message": "Worker deleted"}


@router.patch("/workers/{worker_id}/reactivate")
async def reactivate_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Reactivate a stopped worker by setting status to active."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.status = "active"
    worker.updated_at = _utcnow()
    await db.commit()
    await db.refresh(worker)
    return worker
