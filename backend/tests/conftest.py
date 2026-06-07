from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db import models  # noqa: F401 — register models on Base.metadata
from app.db.base import Base
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """A dedicated `<db>_test` database, created once and torn down per test."""
    base, _, dbname = settings.database_url.rpartition("/")
    test_db = f"{dbname}_test"
    admin = create_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT", future=True)
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": test_db}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{test_db}"'))
    admin.dispose()

    eng = create_engine(f"{base}/{test_db}", future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up: delete children before parents.
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture()
def api_client(engine: Engine) -> Iterator[TestClient]:
    """TestClient whose get_db points at the test database, pre-authenticated."""
    from app.api.deps import get_db

    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    def _override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {settings.api_bearer_token}"})
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        cleanup = factory()
        try:
            for table in reversed(Base.metadata.sorted_tables):
                cleanup.execute(table.delete())
            cleanup.commit()
        finally:
            cleanup.close()
