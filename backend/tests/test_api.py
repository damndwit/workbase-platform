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

def test_invitation_roles_and_shared_workspace(client):
    owner=account(client,"Owner")
    editor=account(client,"Editor")
    viewer=account(client,"Viewer")
    outsider=account(client,"Outsider")
    owner_ws=client.get("/api/auth/me",headers=owner).json()["home_workspace_id"]
    owner_client=client.post("/api/clients",headers=owner,json={"name":"Shared Client","email":"shared@example.org"})
    assert owner_client.status_code==201
    client_id=owner_client.json()["id"]
    for user_email,role in (("editor@example.org","editor"),("viewer@example.org","viewer")):
        created=client.post(f"/api/workspaces/{owner_ws}/invite",headers=owner,json={"email":user_email,"role":role})
        assert created.status_code==201, created.text
    assert client.post(f"/api/workspaces/{owner_ws}/invite",headers=outsider,json={"email":"owner@example.org","role":"viewer"}).status_code==403
    assert client.get(f"/api/workspaces/{owner_ws}/members",headers=outsider).status_code==403
    assert client.get("/api/clients",headers={**viewer,"X-Workspace-Id":str(owner_ws)}).status_code==403
    for auth in (editor,viewer):
        pending=client.get("/api/invitations",headers=auth).json()
        assert len(pending)==1
        assert client.post(f"/api/invitations/{pending[0]['id']}/accept",headers=auth).status_code==204
        assert len(client.get("/api/workspaces",headers=auth).json())==2
    shared_editor={**editor,"X-Workspace-Id":str(owner_ws)}
    shared_viewer={**viewer,"X-Workspace-Id":str(owner_ws)}
    assert len(client.get("/api/clients",headers=shared_editor).json())==1
    assert len(client.get("/api/clients",headers=shared_viewer).json())==1
    assert client.post("/api/clients",headers=shared_viewer,json={"name":"No write","email":"no@example.org"}).status_code==403
    assert client.delete(f"/api/clients/{client_id}",headers=shared_editor).status_code==403
    created=client.post("/api/projects",headers=shared_editor,json={"title":"Shared project","client_id":client_id})
    assert created.status_code==201,created.text
    pid=created.json()["id"]
    assert client.patch(f"/api/projects/{pid}",headers=shared_viewer,json={"status":"done"}).status_code==403
    assert client.patch(f"/api/projects/{pid}",headers=shared_editor,json={"status":"done"}).status_code==200
    assert client.get("/api/summary",headers=shared_viewer).json()["completed_projects"]==1
    assert client.get("/api/summary",headers=outsider).json()["clients"]==0
    assert client.post(f"/api/invitations/9999/accept",headers=owner).status_code==404

def test_ticket_permissions_and_workspace_isolation(client):
    alice=account(client,"Alice")
    bob=account(client,"Bob")
    c=client.post("/api/clients",headers=alice,json={"name":"Customer","email":"customer@example.org"})
    assert c.status_code==201
    cid=c.json()["id"]
    assert client.get("/api/tickets").status_code==401
    assert client.post("/api/tickets",headers=bob,json={"client_id":cid,"subject":"Unauthorized"}).status_code==404
    r=client.post("/api/tickets",headers=alice,json={"client_id":cid,"subject":"Broken checkout","priority":"high","description":"Test ticket"})
    assert r.status_code==201,r.text
    tid=r.json()["id"]
    assert client.get("/api/summary",headers=alice).json()["high_priority_tickets"]==1
    assert client.get("/api/summary",headers=bob).json()["open_tickets"]==0
    assert client.get("/api/tickets",headers=bob).json()==[]
    assert client.patch(f"/api/tickets/{tid}",headers=bob,json={"status":"resolved"}).status_code==404
    assert client.delete(f"/api/tickets/{tid}",headers=bob).status_code==404
    assert client.post("/api/tickets",headers=alice,json={"client_id":cid,"subject":"ok","priority":"invalid"}).status_code==422
    assert client.delete(f"/api/clients/{cid}",headers=alice).status_code==409
    assert client.patch(f"/api/tickets/{tid}",headers=alice,json={"status":"resolved"}).status_code==200
    assert client.get("/api/summary",headers=alice).json()["open_tickets"]==0
    assert client.delete(f"/api/tickets/{tid}",headers=alice).status_code==204
    assert client.delete(f"/api/clients/{cid}",headers=alice).status_code==204

def test_public_demo_is_read_only_and_registration_disabled(client,monkeypatch):
    from app import main,security
    from app.models import User,Workspace
    from app.security import hash_password
    from app.database import get_session

    # Use the fixture's database override to insert the same identity used in production.
    session_generator = app.dependency_overrides[get_session]()
    with next(session_generator) as session:
        demo=User(email=security.DEMO_EMAIL,display_name="Demo Visitor",password_hash=hash_password("random-test-password"))
        session.add(demo)
        session.flush()
        session.add(Workspace(name="Sample workspace",owner_id=demo.id))
        session.commit()

    monkeypatch.setattr(main,"ENVIRONMENT","production")
    monkeypatch.setattr(main,"PUBLIC_DEMO_MODE",True)
    monkeypatch.setattr(security,"PUBLIC_DEMO_MODE",True)
    assert client.post("/api/auth/register",json={
       "display_name":"Another User","workspace_name":"Another Team","email":"another@example.org","password":"safe-demo-password"
    }).status_code==403
    response=client.post("/api/auth/demo")
    assert response.status_code==200,response.text
    headers={"Authorization":"Bearer "+response.json()["access_token"]}
    assert client.get("/api/clients",headers=headers).status_code==200
    assert client.get("/api/workspaces",headers=headers).status_code==200
    assert client.post("/api/clients",headers=headers,json={"name":"Forbidden","email":"forbidden@example.org"}).status_code==403
    assert client.post("/api/projects",headers=headers,json={"title":"Forbidden project","client_id":1}).status_code==403
    assert client.post("/api/tickets",headers=headers,json={"subject":"Forbidden issue","client_id":1}).status_code==403

def test_ticket_conversation_stays_in_workspace(client):
    alice=account(client,"Alice");bob=account(client,"Bob")
    c=client.post("/api/clients",headers=alice,json={"name":"Studio","email":"studio@example.org"})
    ticket=client.post("/api/tickets",headers=alice,json={"client_id":c.json()["id"],"subject":"Website edits"})
    assert ticket.status_code==201
    path=f"/api/tickets/{ticket.json()['id']}/comments"
    assert client.post(path,headers=bob,json={"body":"not mine"}).status_code==404
    created=client.post(path,headers=alice,json={"body":"Sent first draft"})
    assert created.status_code==201,created.text
    assert client.get(path,headers=alice).json()[0]["body"]=="Sent first draft"
    assert client.get(path,headers=bob).status_code==404
    assert client.delete(f"/api/tickets/{ticket.json()['id']}",headers=alice).status_code==204
