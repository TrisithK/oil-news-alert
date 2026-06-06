"""Event-level dedup for ingestion: skip anything we've already stored.

Two signals (§5): the content hash (normalized title+url, enforced UNIQUE at the DB level)
and an exact same-URL check (catches a reworded headline pointing at the same link).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Article


def is_duplicate(session: Session, *, content_hash: str, url: str) -> bool:
    stmt = (
        select(Article.id)
        .where((Article.content_hash == content_hash) | (Article.url == url))
        .limit(1)
    )
    return session.execute(stmt).first() is not None
