"""
Scheduler service for cron and interval-based job scheduling.

Runs as a standalone process. Polls PostgreSQL for due jobs and enqueues them.
Also handles cron-based workflow scheduling.
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta


def _utcnow() -> datetime:
    """Naive UTC datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(UTC).replace(tzinfo=None)

import structlog
from croniter import croniter
from sqlalchemy import select, and_

from app.config import settings
from app.database import async_session, init_db
from app.models.models import Job, Workflow, JobStatus, ScheduleType, WorkflowExecution, WorkflowStatus
from app.core.redis_client import get_redis, JobQueue

logger = structlog.get_logger()


class Scheduler:
    def __init__(self):
        self.running = True
        self.poll_interval = 10  # seconds

    async def start(self):
        logger.info("scheduler_starting")
        await init_db()
        await get_redis()
        
        logger.info("scheduler_started", poll_interval=self.poll_interval)
        
        while self.running:
            try:
                await self._tick()
            except Exception as e:
                logger.error("scheduler_tick_error", error=str(e))
            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        self.running = False
        logger.info("scheduler_stopped")

    async def _tick(self):
        """Main scheduler tick: check for due jobs and workflows."""
        await self._process_scheduled_jobs()
        await self._process_cron_jobs()
        await self._process_workflow_schedules()
        await self._process_delayed_jobs()

    async def _process_scheduled_jobs(self):
        """Enqueue jobs whose scheduled_at time has passed."""
        async with async_session() as db:
            now = _utcnow()
            result = await db.execute(
                select(Job).where(
                    and_(
                        Job.status == JobStatus.PENDING,
                        Job.scheduled_at <= now,
                        Job.scheduled_at.isnot(None),
                        Job.workflow_id.is_(None),  # Don't pick up workflow tasks
                    )
                ).limit(50)
            )
            jobs = result.scalars().all()
            
            for job in jobs:
                job.status = JobStatus.QUEUED
                queue = JobQueue(job.queue_name)
                await queue.enqueue(str(job.id), job.priority.value)
                logger.info("scheduled_job_enqueued", job_id=str(job.id), name=job.name)
            
            if jobs:
                await db.commit()

    async def _process_cron_jobs(self):
        """Process cron-based recurring jobs."""
        async with async_session() as db:
            result = await db.execute(
                select(Job).where(
                    and_(
                        Job.schedule_type == ScheduleType.CRON,
                        Job.cron_expression.isnot(None),
                    )
                ).limit(100)
            )
            jobs = result.scalars().all()
            now = _utcnow()
            
            for job in jobs:
                # Check if this cron expression fires now (within poll interval)
                try:
                    cron = croniter(job.cron_expression, now - timedelta(seconds=self.poll_interval))
                    next_run = cron.get_next(datetime)
                    
                    if next_run <= now:
                        # Create a new one-shot job from the template
                        new_job = Job(
                            name=f"{job.name} (cron)",
                            description=job.description,
                            command=job.command,
                            payload=job.payload or {},
                            priority=job.priority,
                            queue_name=job.queue_name,
                            max_retries=job.max_retries,
                            timeout_seconds=job.timeout_seconds,
                            status=JobStatus.QUEUED,
                            owner_id=job.owner_id,
                        )
                        db.add(new_job)
                        
                        queue = JobQueue(job.queue_name)
                        await queue.enqueue(str(new_job.id), job.priority.value)
                        logger.info("cron_job_enqueued", job_id=str(new_job.id), cron=job.cron_expression)
                        
                except Exception as e:
                    logger.error("cron_parse_error", job_id=str(job.id), error=str(e))
            
            await db.commit()

    async def _process_workflow_schedules(self):
        """Process cron/interval-based workflow schedules."""
        async with async_session() as db:
            now = _utcnow()
            
            result = await db.execute(
                select(Workflow).where(
                    Workflow.schedule_type.in_([ScheduleType.CRON, ScheduleType.INTERVAL])
                ).limit(100)
            )
            workflows = result.scalars().all()
            
            for wf in workflows:
                should_run = False
                
                if wf.schedule_type == ScheduleType.CRON and wf.cron_expression:
                    try:
                        cron = croniter(wf.cron_expression, now - timedelta(seconds=self.poll_interval))
                        next_run = cron.get_next(datetime)
                        should_run = next_run <= now
                    except Exception as e:
                        logger.error("workflow_cron_error", wf_id=str(wf.id), error=str(e))
                        
                elif wf.schedule_type == ScheduleType.INTERVAL and wf.interval_seconds:
                    # Check last execution
                    last_exec_result = await db.execute(
                        select(WorkflowExecution)
                        .where(WorkflowExecution.workflow_id == wf.id)
                        .order_by(WorkflowExecution.created_at.desc())
                        .limit(1)
                    )
                    last_exec = last_exec_result.scalar_one_or_none()
                    
                    if last_exec is None:
                        should_run = True
                    elif last_exec.started_at:
                        next_run = last_exec.started_at + timedelta(seconds=wf.interval_seconds)
                        should_run = next_run <= now
                
                if should_run:
                    # Create a new workflow execution
                    await self._trigger_workflow(wf, db)
            
            await db.commit()

    async def _trigger_workflow(self, wf, db):
        """Trigger a new workflow execution."""
        from app.api.workflows import run_workflow as _unused  # Ensure DAG validation is available
        
        execution = WorkflowExecution(
            workflow_id=wf.id,
            status=WorkflowStatus.RUNNING,
            task_states={},
            started_at=_utcnow(),
        )
        db.add(execution)
        await db.flush()
        
        tasks = wf.dag_definition.get("tasks", {})
        task_jobs = {}
        
        for task_id, task_def in tasks.items():
            job = Job(
                name=f"{wf.name} / {task_def.get('name', task_id)}",
                command=task_def["command"],
                payload={
                    **task_def.get("payload", {}),
                    "_workflow_id": str(wf.id),
                    "_execution_id": str(execution.id),
                    "_task_id": task_id,
                },
                workflow_id=wf.id,
                max_retries=task_def.get("max_retries", 3),
                timeout_seconds=task_def.get("timeout_seconds", 300),
                status=JobStatus.PENDING,
            )
            db.add(job)
            await db.flush()
            task_jobs[task_id] = job
            execution.task_states[task_id] = {"status": "pending", "job_id": str(job.id)}
        
        # Enqueue root tasks
        for task_id, task_def in tasks.items():
            if not task_def.get("depends_on"):
                job = task_jobs[task_id]
                job.status = JobStatus.QUEUED
                queue = JobQueue()
                await queue.enqueue(str(job.id))
                execution.task_states[task_id]["status"] = "queued"
        
        logger.info("workflow_triggered", wf_id=str(wf.id), execution_id=str(execution.id))

    async def _process_delayed_jobs(self):
        """Process jobs that were scheduled for later and are now due."""
        async with async_session() as db:
            now = _utcnow()
            result = await db.execute(
                select(Job).where(
                    and_(
                        Job.status == JobStatus.PENDING,
                        Job.run_at <= now,
                        Job.run_at.isnot(None),
                    )
                ).limit(50)
            )
            jobs = result.scalars().all()
            
            for job in jobs:
                job.status = JobStatus.QUEUED
                queue = JobQueue(job.queue_name)
                await queue.enqueue(str(job.id), job.priority.value)
            
            if jobs:
                await db.commit()


def main():
    scheduler = Scheduler()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(scheduler.start())
    except KeyboardInterrupt:
        loop.run_until_complete(scheduler.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
