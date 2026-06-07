"""Shared API dependencies: DB session and the (single, demo) current user."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import User
from worker.seeds import DEMO_USER_EMAIL, seed_demo_config


def get_current_user(db: Session = Depends(get_db)) -> User:
    """The single MVP trader. Seeded on first use so the API works on a fresh DB."""
    user = db.execute(select(User).where(User.email == DEMO_USER_EMAIL)).scalar_one_or_none()
    if user is None:
        seed_demo_config(db)
        user = db.execute(select(User).where(User.email == DEMO_USER_EMAIL)).scalar_one()
    return user


__all__ = ["get_db", "get_current_user"]
