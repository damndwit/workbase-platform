"""Request/response contracts used by the FastAPI endpoints."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

ClientStatus = Literal["lead", "active", "inactive"]
ProjectStatus = Literal["planned", "in_progress", "done"]

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

class DashboardSummary(BaseModel):
    clients: int
    active_clients: int
    projects: int
    completed_projects: int
