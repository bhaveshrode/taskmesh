"""Built-in job runner that executes commands and built-in tasks."""

import asyncio
import importlib
import traceback
from datetime import UTC, datetime


def _utcnow() -> datetime:
    """Naive UTC datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(UTC).replace(tzinfo=None)
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Job, JobLog, JobStatus


# Registry of built-in tasks that don't require shell execution
BUILTIN_TASKS: dict[str, Any] = {}


def register_task(name: str):
    """Decorator to register a built-in task."""
    def decorator(func):
        BUILTIN_TASKS[name] = func
        return func
    return decorator


@register_task("noop")
async def noop_task(payload: dict) -> dict:
    """Do nothing. Useful for testing."""
    await asyncio.sleep(1)
    return {"message": "noop completed"}


@register_task("echo")
async def echo_task(payload: dict) -> dict:
    """Echo back the payload."""
    await asyncio.sleep(0.5)
    return {"echo": payload}


@register_task("transform")
async def transform_task(payload: dict) -> dict:
    """Transform data using a Python expression."""
    data = payload.get("data", [])
    expression = payload.get("expression", "x")
    results = []
    for item in data:
        result = eval(expression, {"x": item, "__builtins__": {}})
        results.append(result)
    return {"results": results}


@register_task("aggregate")
async def aggregate_task(payload: dict) -> dict:
    """Aggregate data with a simple reduce."""
    data = payload.get("data", [])
    operation = payload.get("operation", "sum")
    if operation == "sum":
        return {"result": sum(data)}
    elif operation == "mean":
        return {"result": sum(data) / len(data) if data else 0}
    elif operation == "count":
        return {"result": len(data)}
    elif operation == "min":
        return {"result": min(data) if data else None}
    elif operation == "max":
        return {"result": max(data) if data else None}
    return {"error": f"Unknown operation: {operation}"}


@register_task("delay")
async def delay_task(payload: dict) -> dict:
    """Sleep for a specified number of seconds."""
    seconds = min(payload.get("seconds", 1), 60)
    await asyncio.sleep(seconds)
    return {"slept_for": seconds}


@register_task("http_request")
async def http_request_task(payload: dict) -> dict:
    """Make an HTTP request."""
    import httpx
    url = payload.get("url", "")
    method = payload.get("method", "GET").upper()
    headers = payload.get("headers", {})
    body = payload.get("body")
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, url, headers=headers, json=body)
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:10000],
        }


async def run_job(job: Job, db: AsyncSession) -> dict[str, Any]:
    """Execute a job and return the result."""
    command = job.command
    payload = job.payload or {}
    start_time = _utcnow()
    
    try:
        # Check if it's a built-in task
        if command in BUILTIN_TASKS:
            result = await BUILTIN_TASKS[command](payload)
        else:
            # Execute as a shell command
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"PAYLOAD": str(payload)},
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=job.timeout_seconds,
            )
            
            result = {
                "stdout": stdout.decode(errors="replace")[:50000],
                "stderr": stderr.decode(errors="replace")[:50000],
                "exit_code": proc.returncode,
            }
            
            if proc.returncode != 0:
                raise RuntimeError(f"Command failed with exit code {proc.returncode}: {result['stderr'][:500]}")

        elapsed = (_utcnow() - start_time).total_seconds()
        
        # Log success
        log = JobLog(
            job_id=job.id,
            level="info",
            message=f"Job completed successfully in {elapsed:.2f}s",
            extra={"elapsed_seconds": elapsed},
        )
        db.add(log)
        
        return {"result": result, "elapsed": elapsed}
        
    except asyncio.TimeoutError:
        elapsed = (_utcnow() - start_time).total_seconds()
        log = JobLog(
            job_id=job.id,
            level="error",
            message=f"Job timed out after {elapsed:.2f}s (limit: {job.timeout_seconds}s)",
        )
        db.add(log)
        raise
        
    except Exception as e:
        elapsed = (_utcnow() - start_time).total_seconds()
        log = JobLog(
            job_id=job.id,
            level="error",
            message=f"Job failed: {str(e)}",
            extra={"traceback": traceback.format_exc()[:5000]},
        )
        db.add(log)
        raise
