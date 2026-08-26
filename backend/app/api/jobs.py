"""Job management API routes."""

from datetime import UTC, datetime


def _utcnow() -> datetime:
    """Naive UTC datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(UTC).replace(tzinfo=None)
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import Job, JobStatus, JobPriority
from app.schemas.schemas import JobCreate, JobUpdate, JobResponse, JobListResponse
from app.core.auth import get_current_user
from app.core.redis_client import JobQueue

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    priority: str = Query(None),
    queue_name: str = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job)
    count_query = select(func.count(Job.id))
    filters = []
    
    if status:
        filters.append(Job.status == status)
    if priority:
        filters.append(Job.priority == priority)
    if queue_name:
        filters.append(Job.queue_name == queue_name)
    if search:
        filters.append(Job.name.ilike(f"%{search}%"))
    
    if filters:
        condition = and_(*filters)
        query = query.where(condition)
        count_query = count_query.where(condition)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return JobListResponse(jobs=jobs, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    job = Job(
        name=job_data.name,
        description=job_data.description,
        command=job_data.command,
        payload=job_data.payload,
        priority=job_data.priority,
        queue_name=job_data.queue_name,
        max_retries=job_data.max_retries,
        timeout_seconds=job_data.timeout_seconds,
        scheduled_at=job_data.scheduled_at,
        tags=job_data.tags,
        owner_id=user.id,
    )
    
    if job_data.scheduled_at and job_data.scheduled_at > _utcnow():
        job.status = JobStatus.PENDING
    else:
        job.status = JobStatus.QUEUED
        queue = JobQueue(job_data.queue_name)
        await queue.enqueue(str(job.id), job_data.priority)
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    job_data: JobUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_data = job_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)
    job.updated_at = _utcnow()
    
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/run", response_model=JobResponse)
async def run_job_now(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Enqueue a job for immediate execution."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = JobStatus.QUEUED
    job.attempt = 0
    job.error_message = None
    job.exit_code = None
    job.result = None
    job.worker_id = None
    job.started_at = None
    job.completed_at = None
    
    queue = JobQueue(job.queue_name)
    await queue.enqueue(str(job.id), job.priority)
    
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in (JobStatus.SUCCESS, JobStatus.FAILED):
        raise HTTPException(status_code=400, detail="Job already completed")
    
    job.status = JobStatus.CANCELLED
    job.completed_at = _utcnow()
    
    queue = JobQueue(job.queue_name)
    await queue.complete(str(job.id))
    
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models.models import JobLog
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete related logs first (FK constraint)
    await db.execute(select(JobLog).where(JobLog.job_id == job_id))
    from sqlalchemy import delete as sa_delete
    await db.execute(sa_delete(JobLog).where(JobLog.job_id == job_id))
    await db.delete(job)
    await db.commit()
