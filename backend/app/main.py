"""Workbase protected API for individual demo workspaces."""
from contextlib import asynccontextmanager
import secrets
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from .database import create_tables, get_session, engine
from .email_notifications import send_team_invitation
from .models import Client, Project, User, Workspace, WorkspaceMember, SupportTicket, TicketComment
from .security import current_user, hash_password, verify_password, token_for_user, owned_workspace, workspace_access, require_role, ENVIRONMENT, PUBLIC_DEMO_MODE, DEMO_EMAIL
from .schemas import (
    RegisterRequest, LoginRequest, TokenResponse, AccountRead,
    ClientCreate, ClientRead, ClientUpdate, ProjectCreate, ProjectRead,
    ProjectUpdate, DashboardSummary, WorkspaceRead, InvitationCreate, InvitationRead, MemberRead, TicketCreate, TicketRead, TicketUpdate, TicketCommentCreate, TicketCommentRead,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    if ENVIRONMENT in ("production", "public_demo") and (PUBLIC_DEMO_MODE or os.getenv("WORKBASE_GUEST_PREVIEW", "0") == "1"):
        with Session(engine) as session:
            demo = session.exec(select(User).where(User.email == DEMO_EMAIL)).first()
            if demo is None:
                import secrets
                demo = User(email=DEMO_EMAIL, display_name="Demo Visitor", password_hash=hash_password(secrets.token_urlsafe(45)))
                session.add(demo)
                session.flush()
                ws = Workspace(name="Studio North · Sample", owner_id=demo.id)
                session.add(ws)
                session.flush()
                sample_clients = [
                    Client(name="Cedar & Co.", email="hello@example.org", status="active", workspace_id=ws.id),
                    Client(name="Northline Studio", email="team@example.net", status="active", workspace_id=ws.id),
                    Client(name="Atlas Design", email="contact@example.com", status="lead", workspace_id=ws.id),
                ]
                session.add_all(sample_clients)
                session.flush()
                session.add_all([
                    Project(title="Website redesign", client_id=sample_clients[0].id, workspace_id=ws.id, status="in_progress"),
                    Project(title="Brand guidelines", client_id=sample_clients[1].id, workspace_id=ws.id, status="done"),
                    Project(title="Client onboarding", client_id=sample_clients[2].id, workspace_id=ws.id, status="planned"),
                    SupportTicket(subject="Update landing page copy", description="Example request for the portfolio demo.", priority="medium", status="open", client_id=sample_clients[0].id, workspace_id=ws.id),
                    SupportTicket(subject="Fix contact form", description="Sample support ticket.", priority="high", status="in_progress", client_id=sample_clients[1].id, workspace_id=ws.id),
                    SupportTicket(subject="Review project handoff", description="Sample resolved issue.", priority="low", status="resolved", client_id=sample_clients[2].id, workspace_id=ws.id),
                ])
                session.commit()
    yield

app = FastAPI(title="Workbase API", version="0.4.0", lifespan=lifespan)
origins = os.getenv("FRONTEND_ORIGINS","http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=["GET","POST","PATCH","DELETE"],allow_headers=["Content-Type","Authorization","X-Workspace-Id"])

@app.get("/api/health")
def health(): return {"status":"ok","demo_available":ENVIRONMENT in ("production", "public_demo") and (PUBLIC_DEMO_MODE or os.getenv("WORKBASE_GUEST_PREVIEW","0")=="1")}

@app.post("/api/auth/register",response_model=TokenResponse,status_code=201)
def register(body:RegisterRequest,session:Session=Depends(get_session)):
    if ENVIRONMENT == "public_demo":
        raise HTTPException(403, "Registration disabled in demo mode")
    if ENVIRONMENT == "production":
        code = os.getenv("WORKBASE_SIGNUP_CODE", "")
        if len(code) < 16 or not secrets.compare_digest(body.signup_code or "", code):
            raise HTTPException(403, "A valid invite code is required to register")
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

@app.post("/api/auth/demo",response_model=TokenResponse)
def demo_login(session:Session=Depends(get_session)):
    if ENVIRONMENT not in ("production", "public_demo") or not (PUBLIC_DEMO_MODE or os.getenv("WORKBASE_GUEST_PREVIEW","0")=="1"):
        raise HTTPException(404,"Not found")
    user=session.exec(select(User).where(User.email==DEMO_EMAIL)).first()
    if user is None: raise HTTPException(503,"Demo not initialized")
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
    return AccountRead(id=user.id,email=user.email,display_name=user.display_name,workspace_name=ws.name,home_workspace_id=ws.id)


@app.get("/api/workspaces",response_model=list[WorkspaceRead])
def workspaces(user:User=Depends(current_user),session:Session=Depends(get_session)):
    home=owned_workspace(user,session)
    result=[WorkspaceRead(id=home.id,name=home.name,role="viewer" if user.email == DEMO_EMAIL and (PUBLIC_DEMO_MODE or os.getenv("WORKBASE_GUEST_PREVIEW","0")=="1") else "owner")]
    memberships=session.exec(select(WorkspaceMember).where(WorkspaceMember.user_id==user.id,WorkspaceMember.accepted==True)).all()
    for member in memberships:
        ws=session.get(Workspace,member.workspace_id)
        if ws: result.append(WorkspaceRead(id=ws.id,name=ws.name,role=member.role))
    return result

@app.get("/api/invitations",response_model=list[InvitationRead])
def invitations(user:User=Depends(current_user),session:Session=Depends(get_session)):
    rows=session.exec(select(WorkspaceMember).where(WorkspaceMember.user_id==user.id,WorkspaceMember.accepted==False)).all()
    return [InvitationRead(id=m.id,workspace_id=m.workspace_id,workspace_name=session.get(Workspace,m.workspace_id).name,role=m.role) for m in rows]

@app.post("/api/invitations/{invitation_id}/accept",status_code=204)
def accept_invitation(invitation_id:int,user:User=Depends(current_user),session:Session=Depends(get_session)):
    member=session.get(WorkspaceMember,invitation_id)
    if not member or member.user_id!=user.id or member.accepted:
        raise HTTPException(404,"Invitation not found")
    if PUBLIC_DEMO_MODE and user.email == DEMO_EMAIL:
        raise HTTPException(403,"Read-only account")
    member.accepted=True
    session.add(member);session.commit()

@app.get("/api/workspaces/{workspace_id}/members",response_model=list[MemberRead])
def workspace_members(workspace_id:int,user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws,role=workspace_access(user,session,workspace_id)
    owner=session.get(User,ws.owner_id)
    rows=[MemberRead(id=owner.id,email=owner.email,display_name=owner.display_name,role="owner",accepted=True)]
    for m in session.exec(select(WorkspaceMember).where(WorkspaceMember.workspace_id==ws.id)).all():
        member=session.get(User,m.user_id)
        if member: rows.append(MemberRead(id=member.id,email=member.email,display_name=member.display_name,role=m.role,accepted=m.accepted))
    return rows

@app.post("/api/workspaces/{workspace_id}/invite",status_code=201)
def invite_user(workspace_id:int,body:InvitationCreate,user:User=Depends(current_user),session:Session=Depends(get_session)):
    ws,role=workspace_access(user,session,workspace_id)
    require_role(role,("owner",))
    invited=session.exec(select(User).where(User.email==str(body.email).lower())).first()
    if not invited: raise HTTPException(404,"Ask the person to create a demo account first")
    if invited.id==user.id: raise HTTPException(400,"Cannot invite yourself")
    existing=session.exec(select(WorkspaceMember).where(WorkspaceMember.workspace_id==ws.id,WorkspaceMember.user_id==invited.id)).first()
    if existing: raise HTTPException(409,"User already invited or a member")
    membership=WorkspaceMember(workspace_id=ws.id,user_id=invited.id,role=body.role)
    session.add(membership);session.commit()
    delivery=send_team_invitation(invited.email,ws.name,user.display_name,body.role)
    return {"message":"Invitation saved. Recipient can accept after signing in.","email_status":delivery}

@app.get("/api/clients",response_model=list[ClientRead])
def list_clients(user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id)
    return session.exec(select(Client).where(Client.workspace_id==ws.id).order_by(Client.id.desc())).all()

@app.post("/api/clients",response_model=ClientRead,status_code=201)
def add_client(body:ClientCreate,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id);require_role(role,['owner','editor'])
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
def edit_client(client_id:int,body:ClientUpdate,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id);require_role(role,['owner','editor']);item=find_client(client_id,ws.id,session)
    for key,value in body.model_dump(exclude_unset=True).items():
        if value is None:raise HTTPException(422,"Fields cannot be null")
        setattr(item,key,value)
    session.add(item);session.commit();session.refresh(item)
    return item

@app.delete("/api/clients/{client_id}",status_code=204)
def delete_client(client_id:int,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id);require_role(role,['owner']);item=find_client(client_id,ws.id,session)
    if session.exec(select(SupportTicket).where(SupportTicket.client_id==client_id,SupportTicket.workspace_id==ws.id)).first():
        raise HTTPException(409,"Delete the client’s support tickets first")
    if session.exec(select(Project).where(Project.client_id==client_id,Project.workspace_id==ws.id)).first():
        raise HTTPException(409,"Delete the client's projects first")
    session.delete(item);session.commit()

@app.get("/api/projects",response_model=list[ProjectRead])
def list_projects(user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id)
    return session.exec(select(Project).where(Project.workspace_id==ws.id).order_by(Project.id.desc())).all()

@app.post("/api/projects",response_model=ProjectRead,status_code=201)
def add_project(body:ProjectCreate,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id);require_role(role,['owner','editor'])
    find_client(body.client_id,ws.id,session)
    item=Project(**body.model_dump(),workspace_id=ws.id)
    session.add(item);session.commit();session.refresh(item)
    return item

@app.patch("/api/projects/{project_id}",response_model=ProjectRead)
def edit_project(project_id:int,body:ProjectUpdate,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id);require_role(role,['owner','editor']);item=find_project(project_id,ws.id,session)
    for key,value in body.model_dump(exclude_unset=True).items():
        if value is None:raise HTTPException(422,"Fields cannot be null")
        setattr(item,key,value)
    session.add(item);session.commit();session.refresh(item)
    return item

@app.delete("/api/projects/{project_id}",status_code=204)
def delete_project(project_id:int,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id);require_role(role,['owner']);item=find_project(project_id,ws.id,session)
    session.delete(item);session.commit()

@app.get("/api/summary",response_model=DashboardSummary)
def summary(user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id)
    clients=session.exec(select(Client).where(Client.workspace_id==ws.id)).all()
    projects=session.exec(select(Project).where(Project.workspace_id==ws.id)).all()
    tickets=session.exec(select(SupportTicket).where(SupportTicket.workspace_id==ws.id)).all()
    return DashboardSummary(clients=len(clients),active_clients=sum(c.status=="active" for c in clients),
            projects=len(projects),completed_projects=sum(p.status=="done" for p in projects),
            open_tickets=sum(t.status!="resolved" for t in tickets),
            high_priority_tickets=sum(t.priority=="high" and t.status!="resolved" for t in tickets))

@app.get("/api/tickets",response_model=list[TicketRead])
def list_tickets(user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,_=workspace_access(user,session,x_workspace_id)
    return session.exec(select(SupportTicket).where(SupportTicket.workspace_id==ws.id).order_by(SupportTicket.id.desc())).all()

@app.post("/api/tickets",response_model=TicketRead,status_code=201)
def create_ticket(body:TicketCreate,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id)
    require_role(role,("owner","editor"))
    find_client(body.client_id,ws.id,session)
    item=SupportTicket(**body.model_dump(),workspace_id=ws.id)
    session.add(item);session.commit();session.refresh(item)
    return item

def find_ticket(ticket_id:int,workspace_id:int,session:Session)->SupportTicket:
    ticket=session.get(SupportTicket,ticket_id)
    if ticket is None or ticket.workspace_id!=workspace_id:
        raise HTTPException(404,"Ticket not found")
    return ticket

@app.patch("/api/tickets/{ticket_id}",response_model=TicketRead)
def update_ticket(ticket_id:int,body:TicketUpdate,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id)
    require_role(role,("owner","editor"))
    item=find_ticket(ticket_id,ws.id,session)
    for field,value in body.model_dump(exclude_unset=True).items():
        if value is None: raise HTTPException(422,"Fields cannot be null")
        setattr(item,field,value)
    session.add(item);session.commit();session.refresh(item)
    return item

@app.delete("/api/tickets/{ticket_id}",status_code=204)
def delete_ticket(ticket_id:int,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id)
    require_role(role,("owner",))
    item=find_ticket(ticket_id,ws.id,session)
    session.exec(select(TicketComment).where(TicketComment.ticket_id==ticket_id,TicketComment.workspace_id==ws.id)).all()
    for note in session.exec(select(TicketComment).where(TicketComment.ticket_id==ticket_id,TicketComment.workspace_id==ws.id)).all():
        session.delete(note)
    session.delete(item);session.commit()


@app.get("/api/tickets/{ticket_id}/comments",response_model=list[TicketCommentRead])
def ticket_comments(ticket_id:int,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,_=workspace_access(user,session,x_workspace_id)
    find_ticket(ticket_id,ws.id,session)
    notes=session.exec(select(TicketComment).where(TicketComment.ticket_id==ticket_id,TicketComment.workspace_id==ws.id).order_by(TicketComment.id)).all()
    return [TicketCommentRead(id=n.id,ticket_id=n.ticket_id,author=session.get(User,n.user_id).display_name,body=n.body,created_at=n.created_at) for n in notes]

@app.post("/api/tickets/{ticket_id}/comments",response_model=TicketCommentRead,status_code=201)
def add_ticket_comment(ticket_id:int,body:TicketCommentCreate,user:User=Depends(current_user),session:Session=Depends(get_session),x_workspace_id:int|None=Header(default=None)):
    ws,role=workspace_access(user,session,x_workspace_id)
    require_role(role,("owner","editor"))
    find_ticket(ticket_id,ws.id,session)
    comment=TicketComment(ticket_id=ticket_id,workspace_id=ws.id,user_id=user.id,body=body.body.strip())
    if not comment.body: raise HTTPException(422,"A comment cannot be empty")
    session.add(comment);session.commit();session.refresh(comment)
    return TicketCommentRead(id=comment.id,ticket_id=comment.ticket_id,author=user.display_name,body=comment.body,created_at=comment.created_at)

# Same-origin static hosting: React built by Vite and served with the FastAPI API.
DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST_DIR.is_dir():
    ASSETS_DIR = DIST_DIR / "assets"
    if ASSETS_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/", include_in_schema=False)
    def frontend_index():
        return FileResponse(DIST_DIR / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend_route(path: str):
        if path.startswith(("api/", "docs", "redoc", "openapi.json")):
            raise HTTPException(404, "Not found")
        asset = (DIST_DIR / path).resolve()
        if asset.is_relative_to(DIST_DIR.resolve()) and asset.is_file():
            return FileResponse(asset)
        return FileResponse(DIST_DIR / "index.html")
