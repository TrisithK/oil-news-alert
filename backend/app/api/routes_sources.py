"""List sources; enable/disable or change poll interval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Article, Source
from app.schemas.api import SourceOut, SourcePatch

router = APIRouter(prefix="/api", tags=["sources"])


def _source_out(db: Session, source: Source) -> SourceOut:
    last_fetched = db.scalar(
        select(func.max(Article.fetched_at)).where(Article.source_id == source.id)
    )
    return SourceOut(
        id=source.id,
        name=source.name,
        kind=source.kind,
        url=source.url,
        reliability_tier=source.reliability_tier,
        poll_interval_sec=source.poll_interval_sec,
        enabled=source.enabled,
        last_fetched_at=last_fetched,
    )


@router.get("/sources", response_model=list[SourceOut])
def get_sources(db: Session = Depends(get_db)) -> list[SourceOut]:
    sources = db.execute(select(Source).order_by(Source.id)).scalars().all()
    return [_source_out(db, s) for s in sources]


@router.patch("/sources/{source_id}", response_model=SourceOut)
def patch_source(source_id: int, payload: SourcePatch, db: Session = Depends(get_db)) -> SourceOut:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found")
    if payload.enabled is not None:
        source.enabled = payload.enabled
    if payload.poll_interval_sec is not None:
        source.poll_interval_sec = payload.poll_interval_sec
    db.commit()
    db.refresh(source)
    return _source_out(db, source)
