"""Small stats dashboard backend (spec §10/§14)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Alert, Analysis, Article, Feedback
from app.schemas.api import Stats

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=Stats)
def get_stats(db: Session = Depends(get_db)) -> Stats:
    total_articles = db.scalar(select(func.count()).select_from(Article)) or 0
    total_analyses = db.scalar(select(func.count()).select_from(Analysis)) or 0
    relevant = (
        db.scalar(select(func.count()).select_from(Analysis).where(Analysis.is_relevant.is_(True)))
        or 0
    )
    total_alerts = db.scalar(select(func.count()).select_from(Alert)) or 0

    by_category = {
        (cat or "unknown"): count
        for cat, count in db.execute(
            select(Analysis.event_category, func.count())
            .where(Analysis.is_relevant.is_(True))
            .group_by(Analysis.event_category)
        ).all()
    }
    by_direction = {
        (direction or "unknown"): count
        for direction, count in db.execute(
            select(Analysis.expected_direction, func.count())
            .where(Analysis.is_relevant.is_(True))
            .group_by(Analysis.expected_direction)
        ).all()
    }
    avg_importance = db.scalar(
        select(func.avg(Analysis.importance_score)).where(Analysis.is_relevant.is_(True))
    )

    feedback_counts = dict(
        db.execute(select(Feedback.label, func.count()).group_by(Feedback.label)).all()
    )
    useful = feedback_counts.get("useful", 0)
    noise = feedback_counts.get("noise", 0)
    useful_ratio = useful / (useful + noise) if (useful + noise) else None

    pairs = db.execute(
        select(Alert.created_at, Article.fetched_at)
        .join(Analysis, Alert.analysis_id == Analysis.id)
        .join(Article, Analysis.article_id == Article.id)
    ).all()
    deltas = [
        (created - fetched).total_seconds() for created, fetched in pairs if created and fetched
    ]
    avg_tta = sum(deltas) / len(deltas) if deltas else None

    tokens = db.execute(
        select(
            func.coalesce(func.sum(Analysis.prompt_tokens), 0),
            func.coalesce(func.sum(Analysis.completion_tokens), 0),
        )
    ).first()

    return Stats(
        total_articles=total_articles,
        total_analyses=total_analyses,
        relevant_analyses=relevant,
        total_alerts=total_alerts,
        by_category=by_category,
        by_direction=by_direction,
        avg_importance=round(avg_importance, 1) if avg_importance is not None else None,
        feedback_counts=feedback_counts,
        feedback_useful_ratio=round(useful_ratio, 2) if useful_ratio is not None else None,
        avg_time_to_alert_sec=round(avg_tta, 1) if avg_tta is not None else None,
        total_prompt_tokens=int(tokens[0]) if tokens else 0,
        total_completion_tokens=int(tokens[1]) if tokens else 0,
    )
