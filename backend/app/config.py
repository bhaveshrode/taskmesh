"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://freebuff:freebuff_secret@localhost:5432/freebuff"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    
    # Worker settings
    WORKER_CONCURRENCY: int = 4
    HEARTBEAT_INTERVAL: int = 15
    JOB_LEASE_SECONDS: int = 300
    MAX_RETRIES: int = 3
    
    # Queue names
    QUEUE_DEFAULT: str = "jobs:default"
    QUEUE_HIGH: str = "jobs:high"
    QUEUE_LOW: str = "jobs:low"
    
    class Config:
        env_file = ".env"


settings = Settings()
