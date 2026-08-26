"""Tests for the FastAPI REST API."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    resp = await client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "testuser"
    
    # Login
    resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_create_and_list_jobs(client):
    # Register and login first
    await client.post("/api/auth/register", json={
        "username": "jobtest",
        "email": "jobtest@example.com",
        "password": "password123",
    })
    login_resp = await client.post("/api/auth/login", json={
        "username": "jobtest",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a job
    resp = await client.post("/api/jobs", json={
        "name": "Test Job",
        "command": "echo",
        "payload": {"message": "hello"},
    }, headers=headers)
    assert resp.status_code == 201
    job = resp.json()
    assert job["name"] == "Test Job"
    assert job["status"] in ("pending", "queued")
    
    # List jobs
    resp = await client.get("/api/jobs", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_create_workflow(client):
    # Register and login
    await client.post("/api/auth/register", json={
        "username": "wftest",
        "email": "wftest@example.com",
        "password": "password123",
    })
    login_resp = await client.post("/api/auth/login", json={
        "username": "wftest",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create workflow
    resp = await client.post("/api/workflows", json={
        "name": "Test Pipeline",
        "description": "A test workflow",
        "tasks": [
            {"id": "a", "name": "Step A", "command": "echo", "depends_on": []},
            {"id": "b", "name": "Step B", "command": "echo", "depends_on": ["a"]},
            {"id": "c", "name": "Step C", "command": "echo", "depends_on": ["a"]},
            {"id": "d", "name": "Step D", "command": "echo", "depends_on": ["b", "c"]},
        ],
    }, headers=headers)
    assert resp.status_code == 201
    wf = resp.json()
    assert wf["name"] == "Test Pipeline"
    assert len(wf["dag_definition"]["tasks"]) == 4


@pytest.mark.asyncio
async def test_workflow_cycle_detection(client):
    await client.post("/api/auth/register", json={
        "username": "cycle_test",
        "email": "cycle@example.com",
        "password": "password123",
    })
    login_resp = await client.post("/api/auth/login", json={
        "username": "cycle_test",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create workflow with cycle
    resp = await client.post("/api/workflows", json={
        "name": "Cyclic",
        "tasks": [
            {"id": "a", "name": "A", "command": "echo", "depends_on": ["b"]},
            {"id": "b", "name": "B", "command": "echo", "depends_on": ["a"]},
        ],
    }, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_dashboard_stats(client):
    resp = await client.get("/api/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_jobs" in data
    assert "active_workers" in data


@pytest.mark.asyncio
async def test_workers_endpoint(client):
    resp = await client.get("/api/workers")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
