"""
Custom distributed worker system.

Design:
- Each worker runs as an independent async process
- Registers itself in PostgreSQL with periodic heartbeats to Redis
- Pulls jobs from Redis priority queue with distributed locking
- Executes jobs with lease-based ownership (prevents duplicate execution)
- Handles retries with exponential backoff
- Detects stale jobs from crashed workers and requeues them
- Continues workflow DAG execution after task completion
"""

import asyncio
import os
import signal
import socket
import sys
import time
from datetime import UTC, datetime, timedelta


def _utcnow() -> datetime:
    """Naive UTC datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(UTC).replace(tzinfo=None)
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session, init_db
from app.models.models import (
    Job, JobStatus, JobLog, Worker, WorkflowExecution,
    WorkflowStatus, Workflow
)
from app.core.redis_client import get_redis, JobQueue, DistributedLock
from app.core.runner import run_job

logger = structlog.get_logger()

WORKER_ID = f"worker-{socket.gethostname()}-{os.getpid()}"


class WorkerProcess:
    def __init__(self):
        self.worker_id = WORKER_ID
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.running = True
        self.current_jobs: set[str] = set()
        self.max_concurrent = settings.WORKER_CONCURRENCY
        self.queues = ["default"]
        self.jobs_completed = 0
        self.jobs_failed = 0
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stale_checker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Initialize the worker."""
        logger.info("worker_starting", worker_id=self.worker_id)
        await init_db()
        await get_redis()
        
        # Register worker in DB
        await self._register()
        
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._stale_checker_task = asyncio.create_task(self._stale_check_loop())
        
        logger.info("worker_started", worker_id=self.worker_id, max_concurrent=self.max_concurrent)
        
        # Main loop
        await self._work_loop()

    async def stop(self):
        """Graceful shutdown."""
        logger.info("worker_stopping", worker_id=self.worker_id)
        self.running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._stale_checker_task:
            self._stale_checker_task.cancel()
        
        # Wait for current jobs to finish (with timeout)
        deadline = time.time() + 30
        while self.current_jobs and time.time() < deadline:
            logger.info("worker_waiting_jobs", remaining=len(self.current_jobs))
            await asyncio.sleep(1)
        
        await self._deregister()
        logger.info("worker_stopped", worker_id=self.worker_id)

    async def _work_loop(self):
        """Main work loop: dequeue and execute jobs."""
        while self.running:
            try:
                # Respect concurrency limit
                if len(self.current_jobs) >= self.max_concurrent:
                    await asyncio.sleep(0.5)
                    continue
                
                # Try to dequeue a job
                for queue_name in self.queues:
                    queue = JobQueue(queue_name)
                    job_id = await queue.dequeue(self.worker_id)
                    
                    if job_id:
                        # Acquire distributed lock
                        lock = DistributedLock(job_id, ttl=settings.JOB_LEASE_SECONDS)
                        acquired = await lock.acquire(self.worker_id)
                        
                        if acquired:
                            self.current_jobs.add(job_id)
                            asyncio.create_task(self._execute_job(job_id, queue_name))
                            break
                        else:
                            # Another worker got it, requeue
                            await queue.requeue(job_id)
                
                if not self.current_jobs:
                    await asyncio.sleep(1)  # No work, wait a bit
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("work_loop_error", error=str(e))
                await asyncio.sleep(5)

    async def _execute_job(self, job_id: str, queue_name: str):
        """Execute a single job with lease management."""
        lock = DistributedLock(job_id, ttl=settings.JOB_LEASE_SECONDS)
        queue = JobQueue(queue_name)
        
        try:
            async with async_session() as db:
                # Load job
                result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
                job = result.scalar_one_or_none()
                
                if not job:
                    logger.warning("job_not_found", job_id=job_id)
                    return
                
                # Mark as running
                job.status = JobStatus.RUNNING
                job.worker_id = self.worker_id
                job.attempt += 1
                job.started_at = _utcnow()
                job.lease_expires_at = _utcnow() + timedelta(seconds=settings.JOB_LEASE_SECONDS)
                job.heartbeat_at = _utcnow()
                await db.commit()
                
                logger.info("job_started", job_id=job_id, attempt=job.attempt, worker=self.worker_id)
                
                # Start lease renewal
                lease_task = asyncio.create_task(self._renew_lease(job_id))
                
                try:
                    # Execute the job
                    exec_result = await run_job(job, db)
                    
                    # Success
                    job.status = JobStatus.SUCCESS
                    job.result = exec_result.get("result")
                    job.exit_code = 0
                    job.completed_at = _utcnow()
                    self.jobs_completed += 1
                    
                    logger.info("job_completed", job_id=job_id, elapsed=exec_result.get("elapsed"))
                    
                    # If part of a workflow, check if we should continue
                    if job.workflow_id:
                        await self._check_workflow_completion(job.workflow_id, db)
                    
                except Exception as e:
                    # Failure
                    job.error_message = str(e)[:5000]
                    job.exit_code = 1
                    
                    if job.attempt < job.max_retries:
                        # Retry with exponential backoff
                        job.status = JobStatus.RETRYING
                        delay = min(2 ** job.attempt, 60)  # 2, 4, 8, 16, 32, 60 max
                        
                        logger.info("job_retrying", job_id=job_id, attempt=job.attempt, delay=delay)
                        
                        await db.commit()
                        await lock.release(self.worker_id)
                        lease_task.cancel()
                        await queue.complete(job_id)
                        
                        # Schedule retry
                        asyncio.create_task(self._delayed_requeue(job_id, queue_name, job.priority.value, delay))
                        return
                    else:
                        job.status = JobStatus.FAILED
                        job.completed_at = _utcnow()
                        self.jobs_failed += 1
                        
                        logger.error("job_failed_permanently", job_id=job_id, error=str(e))
                        
                        # If workflow, mark task as failed
                        if job.workflow_id:
                            await self._handle_workflow_failure(job.workflow_id, job_id, db)
                
                finally:
                    lease_task.cancel()
                    await db.commit()
                    
        except Exception as e:
            logger.error("execute_job_error", job_id=job_id, error=str(e))
        finally:
            self.current_jobs.discard(job_id)
            await queue.complete(job_id)
            await lock.release(self.worker_id)

    async def _renew_lease(self, job_id: str):
        """Periodically renew the job lease to prevent timeout."""
        while True:
            try:
                await asyncio.sleep(settings.JOB_LEASE_SECONDS // 3)
                lock = DistributedLock(job_id, ttl=settings.JOB_LEASE_SECONDS)
                extended = await lock.extend(self.worker_id)
                if not extended:
                    logger.warning("lease_renewal_failed", job_id=job_id)
                    break
                
                # Update heartbeat in DB
                async with async_session() as db:
                    result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
                    job = result.scalar_one_or_none()
                    if job:
                        job.heartbeat_at = _utcnow()
                        await db.commit()
                        
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def _delayed_requeue(self, job_id: str, queue_name: str, priority: str, delay: int):
        """Requeue a job after a delay for retry."""
        await asyncio.sleep(delay)
        queue = JobQueue(queue_name)
        await queue.enqueue(job_id, priority)
        logger.info("job_requeued", job_id=job_id, delay=delay)

    async def _check_workflow_completion(self, workflow_id: UUID, db: AsyncSession):
        """Check if all tasks in a workflow are done; if so, continue or finish."""
        # Get all jobs in this workflow
        result = await db.execute(
            select(Job).where(Job.workflow_id == workflow_id)
        )
        jobs = result.scalars().all()
        
        task_states = {}
        all_done = True
        any_failed = False
        
        for j in jobs:
            task_id = j.payload.get("_task_id") if j.payload else None
            if task_id:
                task_states[task_id] = {
                    "status": j.status.value,
                    "job_id": str(j.id),
                }
                if j.status in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.RETRYING):
                    all_done = False
                if j.status == JobStatus.FAILED:
                    any_failed = True
        
        # Get workflow
        wf_result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
        wf = wf_result.scalar_one_or_none()
        if not wf:
            return
        
        # Find any ready-to-enqueue tasks (all deps done)
        if not all_done and not any_failed:
            tasks = wf.dag_definition.get("tasks", {})
            for task_id, task_def in tasks.items():
                if task_states.get(task_id, {}).get("status") == "pending":
                    deps = task_def.get("depends_on", [])
                    deps_done = all(
                        task_states.get(d, {}).get("status") == "success"
                        for d in deps
                    )
                    if deps_done:
                        # Find the job for this task
                        for j in jobs:
                            if j.payload and j.payload.get("_task_id") == task_id:
                                j.status = JobStatus.QUEUED
                                queue = JobQueue()
                                await queue.enqueue(str(j.id))
                                break
        
        # Update workflow execution state
        exec_result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.workflow_id == workflow_id
            ).order_by(WorkflowExecution.created_at.desc())
        )
        execution = exec_result.scalar_one_or_none()
        if execution:
            execution.task_states = task_states
            
            if any_failed:
                execution.status = WorkflowStatus.FAILED
                execution.completed_at = _utcnow()
                wf.status = WorkflowStatus.FAILED
            elif all_done:
                execution.status = WorkflowStatus.SUCCESS
                execution.completed_at = _utcnow()
                execution.result = {"all_tasks_completed": True}
                wf.status = WorkflowStatus.SUCCESS
                wf.completed_at = _utcnow()
            
            await db.commit()

    async def _handle_workflow_failure(self, workflow_id: UUID, failed_job_id: str, db: AsyncSession):
        """Handle a workflow task failure."""
        wf_result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
        wf = wf_result.scalar_one_or_none()
        if wf:
            wf.status = WorkflowStatus.FAILED
        
        exec_result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.workflow_id == workflow_id
            ).order_by(WorkflowExecution.created_at.desc())
        )
        execution = exec_result.scalar_one_or_none()
        if execution:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = _utcnow()
            execution.error_message = f"Task {failed_job_id} failed"
        
        await db.commit()

    async def _register(self):
        """Register this worker in the database."""
        async with async_session() as db:
            worker = Worker(
                id=self.worker_id,
                hostname=self.hostname,
                pid=self.pid,
                status="active",
                queues=self.queues,
                max_concurrent=self.max_concurrent,
                current_jobs=[],
                heartbeat_at=_utcnow(),
            )
            db.add(worker)
            await db.commit()
        
        # Set initial heartbeat in Redis
        r = await get_redis()
        await r.set(f"worker:{self.worker_id}:heartbeat", _utcnow().isoformat(), ex=60)

    async def _deregister(self):
        """Remove this worker from the database."""
        async with async_session() as db:
            result = await db.execute(select(Worker).where(Worker.id == self.worker_id))
            worker = result.scalar_one_or_none()
            if worker:
                worker.status = "stopped"
                worker.current_jobs = []
                await db.commit()
        
        r = await get_redis()
        await r.delete(f"worker:{self.worker_id}:heartbeat")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats to Redis."""
        while self.running:
            try:
                await asyncio.sleep(settings.HEARTBEAT_INTERVAL)
                r = await get_redis()
                await r.set(
                    f"worker:{self.worker_id}:heartbeat",
                    _utcnow().isoformat(),
                    ex=settings.HEARTBEAT_INTERVAL * 3,
                )
                
                # Update DB
                async with async_session() as db:
                    result = await db.execute(select(Worker).where(Worker.id == self.worker_id))
                    worker = result.scalar_one_or_none()
                    if worker:
                        worker.heartbeat_at = _utcnow()
                        worker.current_jobs = list(self.current_jobs)
                        worker.jobs_completed = self.jobs_completed
                        worker.jobs_failed = self.jobs_failed
                        await db.commit()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("heartbeat_error", error=str(e))

    async def _stale_check_loop(self):
        """Periodically check for and requeue stale jobs from crashed workers."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                queue = JobQueue()
                stale_job_ids = await queue.health_check_stale(settings.JOB_LEASE_SECONDS)
                
                for job_id in stale_job_ids:
                    async with async_session() as db:
                        result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
                        job = result.scalar_one_or_none()
                        
                        if job and job.status == JobStatus.RUNNING:
                            if job.attempt < job.max_retries:
                                job.status = JobStatus.QUEUED
                                job.worker_id = None
                                job.attempt += 1
                                await db.commit()
                                await queue.requeue(job_id, job.priority.value)
                                logger.warning(
                                    "stale_job_requeued",
                                    job_id=job_id,
                                    attempt=job.attempt,
                                )
                            else:
                                job.status = JobStatus.FAILED
                                job.error_message = "Worker lost - max retries exceeded"
                                job.completed_at = _utcnow()
                                await db.commit()
                                await queue.complete(job_id)
                                logger.error("stale_job_failed", job_id=job_id)
                                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("stale_check_error", error=str(e))


def main():
    worker = WorkerProcess()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.ensure_future(worker.stop()))
    
    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        loop.run_until_complete(worker.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
else:
    # When run as module: python -m app.worker
    main()
