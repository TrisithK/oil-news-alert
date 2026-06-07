"""Analyzed feed: list (filterable, paginated) + one item with full score breakdown."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.taxonomy import EventCategory, Magnitude
from app.db.models import Analysis, Article, Source
from app.schemas.api import FeedDetail, FeedItem, FeedPage, ScoreBreakdown
from worker.analyze.score import importance_breakdown

router = APIRouter(prefix="/api", tags=["feed"])


def _feed_item(analysis: Analysis, article: Article, source: Source | None) -> FeedItem:
    return FeedItem(
        id=analysis.id,
        article_id=analysis.article_id,
        created_at=analysis.created_at,
        importance_score=analysis.importance_score,
        event_category=analysis.event_category,
        expected_direction=analysis.expected_direction,
        magnitude=analysis.magnitude,
        confidence=analysis.confidence,
        time_horizon=analysis.time_horizon,
        instruments_affected=analysis.instruments_affected,
        headline_summary=analysis.headline_summary,
        rationale=analysis.rationale,
        title=article.title,
        url=article.url,
        source_name=source.name if source else None,
        source_tier=source.reliability_tier if source else None,
        published_at=article.published_at,
    )


@router.get("/feed", response_model=FeedPage)
def get_feed(
    db: Session = Depends(get_db),
    min_importance: float = Query(0, ge=0, le=100),
    instrument: str | None = None,
    category: str | None = None,
    since: dt.datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> FeedPage:
    base = (
        select(Analysis, Article, Source)
        .join(Article, Analysis.article_id == Article.id)
        .outerjoin(Source, Article.source_id == Source.id)
        .where(Analysis.is_relevant.is_(True))
    )
    if min_importance:
        base = base.where(Analysis.importance_score >= min_importance)
    if instrument:
        base = base.where(Analysis.instruments_affected.contains([instrument]))
    if category:
        base = base.where(Analysis.event_category == category)
    if since:
        base = base.where(Analysis.created_at >= since)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(limit).offset(offset)
    ).all()
    items = [_feed_item(a, art, src) for a, art, src in rows]
    return FeedPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/feed/{analysis_id}", response_model=FeedDetail)
def get_feed_item(analysis_id: int, db: Session = Depends(get_db)) -> FeedDetail:
    row = db.execute(
        select(Analysis, Article, Source)
        .join(Article, Analysis.article_id == Article.id)
        .outerjoin(Source, Article.source_id == Source.id)
        .where(Analysis.id == analysis_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    analysis, article, source = row

    tier = source.reliability_tier if source else "aggregator"
    try:
        category = (
            EventCategory(analysis.event_category)
            if analysis.event_category
            else EventCategory.OTHER
        )
        magnitude = Magnitude(analysis.magnitude) if analysis.magnitude else Magnitude.MEDIUM
        breakdown = importance_breakdown(
            category=category,
            magnitude=magnitude,
            confidence=analysis.confidence or 0.0,
            source_tier=tier,
            novelty=analysis.novelty or 1.0,
        )
    except ValueError:
        breakdown = {
            "category_weight": 0.0,
            "magnitude": 0.0,
            "confidence": analysis.confidence or 0.0,
            "source_tier": 0.0,
            "novelty": analysis.novelty or 1.0,
            "surprise_factor": 1.0,
            "importance_score": analysis.importance_score or 0.0,
        }

    return FeedDetail(
        **_feed_item(analysis, article, source).model_dump(),
        novelty=analysis.novelty,
        key_entities=analysis.key_entities,
        model_triage=analysis.model_triage,
        model_extract=analysis.model_extract,
        prompt_tokens=analysis.prompt_tokens,
        completion_tokens=analysis.completion_tokens,
        score_breakdown=ScoreBreakdown(**breakdown),
    )
