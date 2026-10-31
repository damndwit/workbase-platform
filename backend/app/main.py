"""Workbase protected API for individual demo workspaces."""
from contextlib import asynccontextmanager
import os
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from .database import create_tables, get_session
from .models import Client, Project, User, Workspace
from .security import current_user, hash_password, verify_password, token_for_user, owned_workspace
from .schemas import (
    RegisterRequest, LoginRequest, TokenResponse, AccountRead,
    ClientCreate, ClientRead, ClientUpdate, ProjectCreate, ProjectRead,
    ProjectUpdate, DashboardSummary,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(title="Workbase API", version="0.2.0", lifespan=lifespan)
origins = os.getenv("FRONTEND_ORIGINS","http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=["GET","POST","PATCH","DELETE"],allow_headers=["Content-Type","Authorization"])

@app.get("/api/health")
def health(): return {"status":"ok"}

@app.post("/api/auth/register",response_model=TokenResponse,status_code=201)
def register(body:RegisterRequest,session:Session=Depends(get_session)):
    email=str(body.email).lower()
    if session.exec(select(User).where(User.email==email)).first():
        raise HTTPException(409,"Account already exists")
    user=User(email=email,display_name=body.display_name,password_hash=hash_password(body.password))
    session.add(user)
    try:
        session.flush()
        session.add(Workspace(name=body.workspace_name,owner_id=user.id))
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409,"Account already exists") from None
    session.refresh(user)
    return TokenResponse(access_token=token_for_user(user))

@app.post("/api/auth/login",response_model=TokenResponse)
def login(body:LoginRequest,session:Session=Depends(get_session)):
    user=session.exec(select(User).where(User.email==str(body.email).lower())).first()
    if not user or not verify_password(body.password,user.password_hash):
        raise HTTPException(401,"Invalid credentials")
    return TokenResponse(access_token=token_for_user(user))

@app.get("/api/auth/me",response_model=AccountRead)
def me(user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session)
    return AccountRead(id=user.id,email=user.email,display_name=user.display_name,workspace_name=ws.name)

@app.get("/api/clients",response_model=list[ClientRead])
def list_clients(user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session)
    return session.exec(select(Client).where(Client.workspace_id==ws.id).order_by(Client.id.desc())).all()

@app.post("/api/clients",response_model=ClientRead,status_code=201)
def add_client(body:ClientCreate,user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session)
    item=Client(**body.model_dump(),workspace_id=ws.id)
    session.add(item);session.commit();session.refresh(item)
    return item

def find_client(client_id:int,workspace_id:int,session:Session):
    item=session.get(Client,client_id)
    if not item or item.workspace_id!=workspace_id: raise HTTPException(404,"Client not found")
    return item

def find_project(project_id:int,workspace_id:int,session:Session):
    item=session.get(Project,project_id)
    if not item or item.workspace_id!=workspace_id: raise HTTPException(404,"Project not found")
    return item

@app.patch("/api/clients/{client_id}",response_model=ClientRead)
def edit_client(client_id:int,body:ClientUpdate,user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session);item=find_client(client_id,ws.id,session)
    for key,value in body.model_dump(exclude_unset=True).items():
        if value is None:raise HTTPException(422,"Fields cannot be null")
        setattr(item,key,value)
    session.add(item);session.commit();session.refresh(item)
    return item

@app.delete("/api/clients/{client_id}",status_code=204)
def delete_client(client_id:int,user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session);item=find_client(client_id,ws.id,session)
    if session.exec(select(Project).where(Project.client_id==client_id,Project.workspace_id==ws.id)).first():
        raise HTTPException(409,"Delete the client's projects first")
    session.delete(item);session.commit()

@app.get("/api/projects",response_model=list[ProjectRead])
def list_projects(user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session)
    return session.exec(select(Project).where(Project.workspace_id==ws.id).order_by(Project.id.desc())).all()

@app.post("/api/projects",response_model=ProjectRead,status_code=201)
def add_project(body:ProjectCreate,user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session)
    find_client(body.client_id,ws.id,session)
    item=Project(**body.model_dump(),workspace_id=ws.id)
    session.add(item);session.commit();session.refresh(item)
    return item

@app.patch("/api/projects/{project_id}",response_model=ProjectRead)
def edit_project(project_id:int,body:ProjectUpdate,user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session);item=find_project(project_id,ws.id,session)
    for key,value in body.model_dump(exclude_unset=True).items():
        if value is None:raise HTTPException(422,"Fields cannot be null")
        setattr(item,key,value)
    session.add(item);session.commit();session.refresh(item)
    return item

@app.delete("/api/projects/{project_id}",status_code=204)
def delete_project(project_id:int,user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session);item=find_project(project_id,ws.id,session)
    session.delete(item);session.commit()

@app.get("/api/summary",response_model=DashboardSummary)
def summary(user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws=owned_workspace(user,session)
    clients=session.exec(select(Client).where(Client.workspace_id==ws.id)).all()
    projects=session.exec(select(Project).where(Project.workspace_id==ws.id)).all()
    return DashboardSummary(clients=len(clients),active_clients=sum(c.status=="active" for c in clients),
            projects=len(projects),completed_projects=sum(p.status=="done" for p in projects))
