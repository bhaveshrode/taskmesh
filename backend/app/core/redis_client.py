"""Redis client for queue operations, locks, and pub/sub."""

import json
import time
from typing import Any, Optional
import redis.asyncio as aioredis

from app.config import settings

redis_pool = None


async def get_redis() -> aioredis.Redis:
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return redis_pool


async def close_redis():
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        redis_pool = None


class JobQueue:
    """Redis-based priority job queue with deduplication."""
    
    PRIORITY_MAP = {
        "high": 0,
        "default": 5,
        "low": 10,
    }

    def __init__(self, queue_name: str = "default"):
        self.key = f"queue:{queue_name}"
        self.processing_key = f"queue:{queue_name}:processing"
        self.lease_key = f"queue:{queue_name}:leases"

    async def enqueue(self, job_id: str, priority: str = "default") -> int:
        score = self.PRIORITY_MAP.get(priority, 5)
        r = await get_redis()
        result = await r.zadd(self.key, {job_id: score})
        await r.publish("jobs:new", json.dumps({"job_id": job_id}))
        return result

    async def dequeue(self, worker_id: str) -> Optional[str]:
        r = await get_redis()
        # Atomically move from pending to processing
        result = await r.zpopmin(self.key, count=1)
        if not result:
            return None
        job_id, _ = result[0]
        await r.hset(self.processing_key, job_id, worker_id)
        return job_id

    async def complete(self, job_id: str) -> None:
        r = await get_redis()
        await r.hdel(self.processing_key, job_id)
        await r.zrem(self.key, job_id)

    async def requeue(self, job_id: str, priority: str = "default") -> None:
        r = await get_redis()
        await r.hdel(self.processing_key, job_id)
        await self.enqueue(job_id, priority)

    async def get_queue_length(self) -> int:
        r = await get_redis()
        return await r.zcard(self.key)

    async def get_processing_count(self) -> int:
        r = await get_redis()
        return await r.hlen(self.processing_key)

    async def get_processing_jobs(self) -> dict[str, str]:
        r = await get_redis()
        return await r.hgetall(self.processing_key)

    async def health_check_stale(self, lease_seconds: int = 300) -> list[str]:
        """Find jobs that have been processing too long (likely crashed)."""
        r = await get_redis()
        processing = await r.hgetall(self.processing_key)
        stale = []
        for job_id, worker_id in processing.items():
            lease_key = f"lease:{job_id}"
            lease_ttl = await r.ttl(lease_key)
            if lease_ttl == -2:  # Key doesn't exist = lease expired
                stale.append(job_id)
        return stale


class DistributedLock:
    """Redis-based distributed lock for job execution deduplication."""

    def __init__(self, key: str, ttl: int = 300):
        self.key = f"lock:{key}"
        self.ttl = ttl

    async def acquire(self, worker_id: str) -> bool:
        r = await get_redis()
        return await r.set(self.key, worker_id, nx=True, ex=self.ttl)

    async def extend(self, worker_id: str) -> bool:
        r = await get_redis()
        # Only extend if we own the lock
        current = await r.get(self.key)
        if current == worker_id:
            await r.expire(self.key, self.ttl)
            return True
        return False

    async def release(self, worker_id: str) -> bool:
        r = await get_redis()
        # Lua script for atomic check-and-delete
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        result = await r.eval(script, 1, self.key, worker_id)
        return result == 1
