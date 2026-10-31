"""API integration tests using a temporary SQLite database."""
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app import models  # noqa: F401

@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as tmp:
        engine=create_engine(f"sqlite:///{Path(tmp) / 'test.db'}", connect_args={"check_same_thread":False})
        SQLModel.metadata.create_all(engine)
        def override():
            with Session(engine) as session: yield session
        app.dependency_overrides[get_session]=override
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()
        engine.dispose()

def test_health_and_initial_summary(client):
    assert client.get("/api/health").json()=={"status":"ok"}
    assert client.get("/api/summary").json()=={"clients":0,"active_clients":0,"projects":0,"completed_projects":0}

def test_client_and_project_lifecycle(client):
    c=client.post("/api/clients",json={"name":"Cedar Studio","email":"hello@example.org","status":"active"})
    assert c.status_code==201
    cid=c.json()["id"]
    p=client.post("/api/projects",json={"title":"Website refresh","client_id":cid})
    assert p.status_code==201
    pid=p.json()["id"]
    assert client.get("/api/summary").json()=={"clients":1,"active_clients":1,"projects":1,"completed_projects":0}
    assert client.patch(f"/api/projects/{pid}",json={"status":"done"}).json()["status"]=="done"
    assert client.get("/api/summary").json()["completed_projects"]==1
    assert client.delete(f"/api/clients/{cid}").status_code==409
    assert client.delete(f"/api/projects/{pid}").status_code==204
    assert client.delete(f"/api/clients/{cid}").status_code==204

def test_validation_and_missing_resources(client):
    assert client.post("/api/clients",json={"name":"A","email":"invalid"}).status_code==422
    assert client.post("/api/projects",json={"title":"A good project","client_id":999}).status_code==404
    assert client.patch("/api/projects/999",json={"status":"done"}).status_code==404
    assert client.delete("/api/clients/999").status_code==404
    assert client.post("/api/clients",json={"name":"Nice company","email":"hello@example.org","status":"unexpected"}).status_code==422
