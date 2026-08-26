# TaskMesh

A distributed job orchestration and workflow platform built with FastAPI, Next.js, PostgreSQL and Redis.

TaskMesh allows users to create and execute background jobs, compose jobs into dependency-based workflows, and monitor worker processes responsible for execution. Redis handles distributed job queuing and locking, while PostgreSQL maintains persistent job, workflow, execution, and worker state.

## Screenshots

### Dashboard
![Dashboard](docs/screenshot-dashboard.png)

### Jobs
![Jobs](docs/screenshot-jobs.png)

### Workflow DAG
![Workflows](docs/screenshot-workflows.png)

### Workers
![Workers](docs/screenshot-workers.png)

## Features

- **Dashboard** - Monitor jobs, workflows, workers, and system activity with automatic status refresh
- **Job Management** - Create, run, retry, cancel, and delete jobs with priority queues
- **Workflow DAG** - Build and execute multi-step workflows with dependency graphs
- **Worker Management** - Monitor worker health, reactivate stopped workers, and remove stopped workers
- **Execution Logs** - View job execution history and logs
- **Authentication** - JWT-based user registration and login
- **Retry Logic** - Automatic job retries with exponential backoff
- **Stale Job Recovery** - Detects and requeues jobs from crashed workers

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                         │
│                    (React + Tailwind CSS)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP API
┌───────────────────────────▼─────────────────────────────────────┐
│                      FastAPI Backend                             │
│                 (Async Python + SQLAlchemy)                      │
└──────────┬──────────────────────────────────┬───────────────────┘
           │                                  │
┌──────────▼──────────┐            ┌──────────▼──────────┐
│    PostgreSQL        │            │       Redis          │
│  (Job/Workflow DB)   │            │  (Queue + Locks)     │
└──────────────────────┘            └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │     Worker Pool      │
                                    │  (Async Processes)   │
                                    └─────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI, Python 3.12 |
| Frontend | Next.js 15, React 19, TypeScript |
| Database | PostgreSQL 15+ |
| Queue | Redis 7+ |
| Auth | JWT (python-jose), bcrypt |
| ORM | SQLAlchemy (async) |
| Styling | Tailwind CSS |

## Project Structure

```
taskmesh/
├── backend/
│   ├── app/
│   │   ├── api/            # API route handlers
│   │   │   ├── auth.py     # Login, register endpoints
│   │   │   ├── jobs.py     # Job CRUD + execution
│   │   │   ├── workflows.py # Workflow CRUD + DAG execution
│   │   │   └── workers.py  # Worker monitoring + management + logs
│   │   ├── core/
│   │   │   ├── auth.py     # JWT + password hashing
│   │   │   ├── redis_client.py # Redis queues + locks
│   │   │   └── runner.py   # Job execution engine
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── config.py       # Environment configuration
│   │   ├── database.py     # DB setup + initialization
│   │   ├── main.py         # FastAPI app
│   │   └── worker.py       # Worker process
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js pages
│   │   ├── components/     # React components
│   │   ├── lib/            # API client
│   │   └── types/          # TypeScript types
│   ├── next.config.js
│   └── package.json
└── README.md
```

## Database Design

### Tables

- **users** - User accounts (admin, regular users)
- **jobs** - Job definitions and execution state
- **job_logs** - Execution logs per job
- **workflows** - DAG workflow definitions
- **workflow_executions** - Workflow run history
- **workers** - Worker registration and heartbeat
- **schedules** - Job/workflow scheduling configuration

### Key Relationships

```
User ─┬─< Job
      └─< Workflow ─< WorkflowExecution
                   └─< Job (with workflow_id)
Job ─< JobLog
```

## Job Execution Flow

1. **Create Job** → Job status: `QUEUED`, added to Redis sorted set
2. **Worker Dequeues** → Acquires distributed lock, status: `RUNNING`
3. **Execute** → Built-in task or shell command with timeout
4. **On Success** → Status: `SUCCESS`, release lock
5. **On Failure** → If retries left: status `RETRYING`, exponential backoff, requeue
6. **Max Retries** → Status: `FAILED`

## Workflow Execution

1. **Run Workflow** → Create `WorkflowExecution` record
2. **Create Jobs** → One job per task in the DAG
3. **Enqueue Roots** → Tasks with no dependencies start immediately
4. **DAG Progression** → Worker checks dependencies after each task completes
5. **Branching** → Parallel branches execute concurrently
6. **Completion** → All tasks done → workflow `SUCCESS`, any failure → `FAILED`

### Example DAG

```
       ┌── B ──┐
A ─────┤       ├── D
       └── C ──┘

- A executes first (no deps)
- B and C run in parallel (depend on A)
- D waits for both B and C
```

## Worker Architecture

- **Registration** - Worker registers in PostgreSQL on startup
- **Heartbeat** - Periodic heartbeat to Redis + PostgreSQL (every 15s)
- **Job Lease** - Distributed lock prevents duplicate execution
- **Lease Renewal** - Extends lock while job is running
- **Stale Detection** - Checks for crashed workers every 60s
- **Graceful Shutdown** - Waits for current jobs (30s timeout)

## Authentication

- **JWT Tokens** - 24-hour token expiration
- **Password Hashing** - bcrypt password hashing
- **User Registration** - Users can create accounts through the frontend
- **User Login** - JWT-based authentication through the frontend
- **Default Admin** - Development admin account automatically created on first run (`admin` / `admin`)
- **Protected Routes** - Authenticated access is required for protected operations

> **Development Note:** Change the default admin credentials before using TaskMesh in any non-local environment.

## Installation

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env

# Start API server
uvicorn app.main:app --reload --port 8080

# Start worker (separate terminal)
python -m app.worker
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Database Setup

```sql
-- Create database and user
CREATE USER freebuff WITH PASSWORD 'freebuff_secret';
CREATE DATABASE freebuff OWNER freebuff;
```

Tables are automatically created on first startup.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://freebuff:freebuff_secret@localhost:5432/freebuff` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `WORKER_CONCURRENCY` | `4` | Maximum concurrent jobs per worker |
| `HEARTBEAT_INTERVAL` | `15` | Worker heartbeat interval (seconds) |
| `JOB_LEASE_SECONDS` | `300` | Job lock timeout (seconds) |
| `MAX_RETRIES` | `3` | Default job retry limit |

## API Documentation

Once running, visit:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login and get JWT |
| `POST` | `/api/auth/register` | Create new user |
| `GET` | `/api/dashboard/stats` | Dashboard statistics |
| `GET/POST` | `/api/jobs` | List/Create jobs |
| `POST` | `/api/jobs/{id}/run` | Execute a job |
| `DELETE` | `/api/jobs/{id}` | Delete a job |
| `GET` | `/api/jobs/{id}/logs` | Get job execution logs |
| `GET/POST` | `/api/workflows` | List/Create workflows |
| `POST` | `/api/workflows/{id}/run` | Execute a workflow |
| `GET` | `/api/workers` | List workers |
| `PATCH` | `/api/workers/{id}/reactivate` | Reactivate stopped worker |
| `DELETE` | `/api/workers/{id}` | Delete stopped worker |

## Known Limitations

1. **Development Deployment** - The current setup is intended for local/development use and is not production-hardened.
2. **Redis Persistence** - Queue durability depends on Redis persistence configuration. The default local development setup does not provide production-grade queue durability.
3. **Authentication Features** - Password reset and email verification are not currently implemented.
4. **No HTTPS** - Local development uses HTTP; production deployments should use HTTPS through a reverse proxy such as nginx or Caddy.
5. **No Automated Horizontal Scaling** - Multiple worker processes can run concurrently, but worker provisioning and scaling are currently managed manually.

## Future Improvements

- [ ] WebSocket for real-time job updates
- [ ] Cron job scheduling UI
- [ ] Job file attachments
- [ ] Workflow versioning
- [ ] Metrics/monitoring (Prometheus)
- [ ] Docker deployment
- [ ] CI/CD pipeline
- [ ] Rate limiting
- [ ] API key authentication
- [ ] Job chaining (output → input)

## License

MIT

---

Built with 🐝 by Bhavesh
