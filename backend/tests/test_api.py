"""Tests for registration, authentication and workspace isolation."""
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session,SQLModel,create_engine
from app.database import get_session
from app.main import app
from app import models  # noqa: F401

@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as temp:
        engine=create_engine(f"sqlite:///{Path(temp)/'test.db'}",connect_args={"check_same_thread":False})
        SQLModel.metadata.create_all(engine)
        def override():
            with Session(engine) as s:yield s
        app.dependency_overrides[get_session]=override
        with TestClient(app) as test:yield test
        app.dependency_overrides.clear()
        engine.dispose()

def account(client,name):
    response=client.post("/api/auth/register",json={
        "display_name":name,"workspace_name":name+" Studio",
        "email":name.lower()+"@example.org","password":"correct-horse-demo-123",
    })
    assert response.status_code==201,response.text
    return {"Authorization":"Bearer "+response.json()["access_token"]}

def test_requires_login(client):
    assert client.get("/api/health").status_code==200
    for route in ("/api/clients","/api/projects","/api/summary","/api/auth/me"):
        assert client.get(route).status_code==401

def test_register_login_and_invalid_login(client):
    h=account(client,"Alice")
    assert client.get("/api/auth/me",headers=h).json()["workspace_name"]=="Alice Studio"
    assert client.post("/api/auth/login",json={"email":"alice@example.org","password":"wrong"}).status_code==401
    assert client.post("/api/auth/login",json={"email":"alice@example.org","password":"correct-horse-demo-123"}).status_code==200
    assert client.post("/api/auth/register",json={
        "display_name":"Alice","workspace_name":"Duplicate","email":"alice@example.org","password":"correct-horse-demo-123",
    }).status_code==409

def test_isolated_crud(client):
    alice=account(client,"Alice");bob=account(client,"Bob")
    response=client.post("/api/clients",headers=alice,json={"name":"Alpha","email":"alpha@example.org","status":"active"})
    assert response.status_code==201,response.text
    cid=response.json()["id"]
    project=client.post("/api/projects",headers=alice,json={"title":"Website","client_id":cid})
    assert project.status_code==201,project.text
    pid=project.json()["id"]
    assert len(client.get("/api/clients",headers=bob).json())==0
    assert len(client.get("/api/projects",headers=bob).json())==0
    assert client.get("/api/summary",headers=bob).json()["clients"]==0
    assert client.patch(f"/api/clients/{cid}",headers=bob,json={"status":"inactive"}).status_code==404
    assert client.delete(f"/api/clients/{cid}",headers=bob).status_code==404
    assert client.post("/api/projects",headers=bob,json={"title":"Intrusion","client_id":cid}).status_code==404
    assert client.patch(f"/api/projects/{pid}",headers=bob,json={"status":"done"}).status_code==404
    assert client.delete(f"/api/projects/{pid}",headers=bob).status_code==404
    assert client.delete(f"/api/clients/{cid}",headers=alice).status_code==409
    assert client.patch(f"/api/projects/{pid}",headers=alice,json={"status":"done"}).status_code==200
    assert client.get("/api/summary",headers=alice).json()["completed_projects"]==1
    assert client.delete(f"/api/projects/{pid}",headers=alice).status_code==204
    assert client.delete(f"/api/clients/{cid}",headers=alice).status_code==204
