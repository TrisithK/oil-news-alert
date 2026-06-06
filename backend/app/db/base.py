"""SQLAlchemy engine, session factory, and declarative base.

Synchronous SQLAlchemy 2.0 with the psycopg3 driver (`postgresql+psycopg://`).
FastAPI endpoints that touch the DB use plain `def` handlers (run in a threadpool);
the async SSE stream reads from an in-memory hub, not the DB hot path.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
