"""Database models for the job and workflow platform."""

import uuid
from datetime import UTC, datetime


def _utcnow() -> datetime:
    """Return current UTC time as a naive datetime (no tzinfo).
    Compatible with TIMESTAMP WITHOUT TIME ZONE columns.
    """
    return datetime.now(UTC).replace(tzinfo=None)
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey,
    Enum as SAEnum, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduleType(str, enum.Enum):
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    WORKFLOW = "workflow"


class JobPriority(str, enum.Enum):
    LOW = "low"
    DEFAULT = "default"
    HIGH = "high"


def generate_uuid():
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=_utcnow)

    jobs = relationship("Job", back_populates="owner")
    workflows = relationship("Workflow", back_populates="owner")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    command = Column(Text, nullable=False)
    payload = Column(JSON, default=dict)
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING, index=True)
    priority = Column(SAEnum(JobPriority), default=JobPriority.DEFAULT, index=True)
    queue_name = Column(String(100), default="default")
    
    # Scheduling
    schedule_type = Column(SAEnum(ScheduleType), default=ScheduleType.ONCE)
    cron_expression = Column(String(100), nullable=True)
    interval_seconds = Column(Integer, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    run_at = Column(DateTime, nullable=True)
    
    # Execution tracking
    attempt = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=300)
    
    # Worker tracking
    worker_id = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)
    
    # Results
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    
    # Metadata
    tags = Column(JSON, default=list)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=True)
    parent_job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=_utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="jobs")
    workflow = relationship("Workflow", back_populates="jobs")
    children = relationship("Job", backref="parent_job", remote_side=[id])
    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_jobs_status_priority", "status", "priority"),
        Index("idx_jobs_worker_id", "worker_id"),
        Index("idx_jobs_scheduled_at", "scheduled_at"),
        Index("idx_jobs_queue_status", "queue_name", "status"),
    )


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    dag_definition = Column(JSON, nullable=False)
    status = Column(SAEnum(WorkflowStatus), default=WorkflowStatus.PENDING, index=True)
    schedule_type = Column(SAEnum(ScheduleType), default=ScheduleType.ONCE)
    cron_expression = Column(String(100), nullable=True)
    interval_seconds = Column(Integer, nullable=True)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=_utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="workflows")
    jobs = relationship("Job", back_populates="workflow")
    executions = relationship("WorkflowExecution", back_populates="workflow")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    status = Column(SAEnum(WorkflowStatus), default=WorkflowStatus.PENDING, index=True)
    
    # Track which tasks have completed
    task_states = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=_utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow", back_populates="executions")


class Worker(Base):
    __tablename__ = "workers"

    id = Column(String(100), primary_key=True)
    hostname = Column(String(255), nullable=False)
    pid = Column(Integer, nullable=False)
    status = Column(String(50), default="active")
    queues = Column(JSON, default=list)
    
    # Resource tracking
    max_concurrent = Column(Integer, default=4)
    current_jobs = Column(JSON, default=list)
    
    # Heartbeat
    heartbeat_at = Column(DateTime, nullable=True)
    
    # Stats
    jobs_completed = Column(Integer, default=0)
    jobs_failed = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=_utcnow)


class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True)
    level = Column(String(20), default="info")
    message = Column(Text, nullable=False)
    extra = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=_utcnow, index=True)

    job = relationship("Job", back_populates="logs")
