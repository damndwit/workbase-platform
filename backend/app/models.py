"""SQLModel tables for Workbase's first client/project management release."""
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    email: str = Field(max_length=160)
    status: str = Field(default="lead", index=True)
    created_at: datetime = Field(default_factory=utc_now)

class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True, max_length=120)
    client_id: int = Field(foreign_key="client.id", index=True)
    status: str = Field(default="planned", index=True)
    created_at: datetime = Field(default_factory=utc_now)
