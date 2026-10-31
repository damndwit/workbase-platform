"""Workbase API: first milestone. No login or tenant isolation yet."""
from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .database import create_tables, get_session
from .models import Client, Project
from .schemas import ClientCreate, ClientRead, ClientUpdate, ProjectCreate, ProjectRead, ProjectUpdate, DashboardSummary

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(title="Workbase API", version="0.1.0", lifespan=lifespan)

origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET","POST","PATCH","DELETE"], allow_headers=["Content-Type"])

@app.get("/api/health")
def health():
    return {"status":"ok"}

@app.get("/api/clients", response_model=list[ClientRead])
def list_clients(session: Session = Depends(get_session)):
    return session.exec(select(Client).order_by(Client.id.desc())).all()

@app.post("/api/clients", response_model=ClientRead, status_code=201)
def add_client(body: ClientCreate, session: Session = Depends(get_session)):
    client=Client(**body.model_dump())
    session.add(client)
    session.commit()
    session.refresh(client)
    return client

@app.patch("/api/clients/{client_id}", response_model=ClientRead)
def edit_client(client_id: int, body: ClientUpdate, session: Session = Depends(get_session)):
    client=session.get(Client,client_id)
    if client is None: raise HTTPException(404,"Client not found")
    for key,value in body.model_dump(exclude_unset=True).items():
        if value is None: raise HTTPException(422,"Fields cannot be null")
        setattr(client,key,value)
    session.add(client)
    session.commit()
    session.refresh(client)
    return client

@app.delete("/api/clients/{client_id}", status_code=204)
def delete_client(client_id: int, session: Session = Depends(get_session)):
    client=session.get(Client,client_id)
    if client is None: raise HTTPException(404,"Client not found")
    if session.exec(select(Project).where(Project.client_id==client_id)).first():
        raise HTTPException(409,"Remove the client's projects first")
    session.delete(client)
    session.commit()

@app.get("/api/projects", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_session)):
    return session.exec(select(Project).order_by(Project.id.desc())).all()

@app.post("/api/projects", response_model=ProjectRead, status_code=201)
def add_project(body: ProjectCreate, session: Session = Depends(get_session)):
    if not session.get(Client,body.client_id):
        raise HTTPException(404,"Client not found")
    project=Project(**body.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project

@app.patch("/api/projects/{project_id}", response_model=ProjectRead)
def edit_project(project_id: int, body: ProjectUpdate, session: Session = Depends(get_session)):
    project=session.get(Project,project_id)
    if project is None: raise HTTPException(404,"Project not found")
    for key,value in body.model_dump(exclude_unset=True).items():
        if value is None: raise HTTPException(422,"Fields cannot be null")
        setattr(project,key,value)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project

@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int, session: Session = Depends(get_session)):
    project=session.get(Project,project_id)
    if project is None: raise HTTPException(404,"Project not found")
    session.delete(project)
    session.commit()

@app.get("/api/summary", response_model=DashboardSummary)
def dashboard_summary(session: Session = Depends(get_session)):
    clients=session.exec(select(Client)).all()
    projects=session.exec(select(Project)).all()
    return DashboardSummary(
        clients=len(clients),
        active_clients=sum(c.status=="active" for c in clients),
        projects=len(projects),
        completed_projects=sum(p.status=="done" for p in projects),
    )
