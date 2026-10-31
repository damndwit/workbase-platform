"""Request and response validation contracts."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Limit the allowed status values.
ClientStatus = Literal["lead", "active", "inactive"]
ProjectStatus = Literal["planned", "in_progress", "done"]

# Signup fields, validated before saving.
class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    workspace_name: str = Field(min_length=2, max_length=100)
    signup_code: str | None = Field(default=None, max_length=160)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Account details for the UI.
class AccountRead(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    workspace_name: str
    home_workspace_id: int

class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"

# Basic client input rules.
class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    status: ClientStatus = "lead"

class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    status: ClientStatus | None = None

class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    status: ClientStatus
    created_at: datetime

# Make sure the client ID is valid.
class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    client_id: int = Field(gt=0)
    status: ProjectStatus = "planned"

class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    status: ProjectStatus | None = None

class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    client_id: int
    status: ProjectStatus
    created_at: datetime

# The overview cards use these counts.
class DashboardSummary(BaseModel):
    clients: int
    active_clients: int
    projects: int
    completed_projects: int
    open_tickets: int = 0
    high_priority_tickets: int = 0

TeamRole = Literal["editor", "viewer"]
WorkspaceRole = Literal["owner", "editor", "viewer"]

class WorkspaceRead(BaseModel):
    id: int
    name: str
    role: WorkspaceRole

# Invite an existing account into a team.
class InvitationCreate(BaseModel):
    email: EmailStr
    role: TeamRole = "viewer"

class InvitationRead(BaseModel):
    id: int
    workspace_id: int
    workspace_name: str
    role: TeamRole

class MemberRead(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    role: WorkspaceRole
    accepted: bool

TicketPriority = Literal["low", "medium", "high"]
TicketStatus = Literal["open", "in_progress", "resolved"]

# A support request has a client and a subject.
class TicketCreate(BaseModel):
    client_id: int = Field(gt=0)
    subject: str = Field(min_length=3, max_length=140)
    description: str = Field(default="", max_length=2000)
    priority: TicketPriority = "medium"

class TicketUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    priority: TicketPriority | None = None
    status: TicketStatus | None = None

class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime

# Ticket notes live in their own table so conversations don't overwrite each other.
# Notes can't be empty.
class TicketCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

class TicketCommentRead(BaseModel):
    id: int
    ticket_id: int
    author: str
    body: str
    created_at: datetime
