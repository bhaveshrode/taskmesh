"""FastAPI main application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.core.redis_client import close_redis
from app.api import auth, jobs, workflows, workers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_redis()


app = FastAPI(
    title="TaskMesh Platform",
    description="Distributed Job & Workflow Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://taskmesh-web.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(workflows.router, prefix="/api")
app.include_router(workers.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "taskmesh-api"}
