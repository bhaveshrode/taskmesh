"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ---- Auth ----
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ---- Jobs ----
class JobCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str = ""
    command: str
    payload: dict[str, Any] = {}
    priority: str = "default"
    queue_name: str = "default"
    max_retries: int = 3
    timeout_seconds: int = 300
    scheduled_at: Optional[datetime] = None
    tags: list[str] = []


class JobUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    command: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    priority: Optional[str] = None
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None
    scheduled_at: Optional[datetime] = None


class JobResponse(BaseModel):
    id: UUID
    name: str
    description: str
    command: str
    payload: dict[str, Any]
    status: str
    priority: str
    queue_name: str
    schedule_type: str
    attempt: int
    max_retries: int
    timeout_seconds: int
    worker_id: Optional[str]
    result: Optional[dict[str, Any]]
    error_message: Optional[str]
    exit_code: Optional[int]
    tags: list[str]
    owner_id: Optional[UUID]
    workflow_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    scheduled_at: Optional[datetime]
    cron_expression: Optional[str]
    interval_seconds: Optional[int]

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


# ---- Workflows ----
class WorkflowTaskDef(BaseModel):
    id: str
    name: str
    command: str
    depends_on: list[str] = []
    payload: dict[str, Any] = {}
    max_retries: int = 3
    timeout_seconds: int = 300


class WorkflowCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str = ""
    tasks: list[WorkflowTaskDef]
    schedule_type: str = "once"
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tasks: Optional[list[WorkflowTaskDef]] = None


class WorkflowResponse(BaseModel):
    id: UUID
    name: str
    description: str
    dag_definition: dict[str, Any]
    status: str
    schedule_type: str
    cron_expression: Optional[str]
    interval_seconds: Optional[int]
    owner_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkflowExecutionResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    status: str
    task_states: dict[str, Any]
    result: Optional[dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ---- Schedules ----
class ScheduleCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str = ""
    command: str
    payload: dict[str, Any] = {}
    schedule_type: str  # once, interval, cron
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[datetime] = None
    queue_name: str = "default"
    priority: str = "default"


# ---- Workers ----
class WorkerResponse(BaseModel):
    id: str
    hostname: str
    pid: int
    status: str
    queues: list[str]
    max_concurrent: int
    current_jobs: list[str]
    heartbeat_at: Optional[datetime]
    jobs_completed: int
    jobs_failed: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---- Logs ----
class LogEntry(BaseModel):
    id: UUID
    job_id: UUID
    level: str
    message: str
    extra: dict[str, Any]
    timestamp: datetime

    model_config = {"from_attributes": True}


# ---- Stats ----
class DashboardStats(BaseModel):
    total_jobs: int
    running_jobs: int
    queued_jobs: int
    failed_jobs: int
    completed_jobs: int
    total_workflows: int
    active_workers: int
    jobs_last_24h: int
