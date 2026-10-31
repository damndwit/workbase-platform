"""Database configuration for local SQLite and hosted PostgreSQL."""
import os
from collections.abc import Generator
from sqlmodel import Session, SQLModel, create_engine

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
provided_url = os.getenv("DATABASE_URL", "").strip()
if ENVIRONMENT == "production" and not provided_url:
    raise RuntimeError("Production requires DATABASE_URL (use a hosted PostgreSQL database).")

DATABASE_URL = provided_url or "sqlite:///./workbase_v2.db"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]

if ENVIRONMENT == "production" and not DATABASE_URL.startswith("postgresql+psycopg://"):
    raise RuntimeError("Production requires PostgreSQL, not a local SQLite database.")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
    pool_pre_ping=True,
    pool_recycle=1200,
)

def create_tables() -> None:
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
