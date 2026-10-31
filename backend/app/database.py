"""Database configuration. SQLite by default; PostgreSQL via DATABASE_URL."""
import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./workbase_v2.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
    pool_pre_ping=True,
)

def create_tables() -> None:
    # Import models before create_all so SQLModel knows about every table.
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
