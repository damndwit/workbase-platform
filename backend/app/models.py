"""Database tables for individual user-owned Workbase demo workspaces."""
from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=160)
    display_name: str = Field(max_length=100)
    password_hash: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=utc_now)

class Workspace(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    owner_id: int = Field(foreign_key="user.id", index=True, unique=True)
    created_at: datetime = Field(default_factory=utc_now)

class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    name: str = Field(index=True, max_length=100)
    email: str = Field(max_length=160)
    status: str = Field(default="lead", index=True)
    created_at: datetime = Field(default_factory=utc_now)

class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    title: str = Field(index=True, max_length=120)
    client_id: int = Field(foreign_key="client.id", index=True)
    status: str = Field(default="planned", index=True)
    created_at: datetime = Field(default_factory=utc_now)

class WorkspaceMember(SQLModel, table=True):
    """Invitation and membership for a workspace a user does not own."""
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(default="viewer")  # editor or viewer
    accepted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)
