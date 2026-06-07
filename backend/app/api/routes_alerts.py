"""Alert history + acknowledge."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Alert, Analysis, Article
from app.schemas.api import AlertOut
from worker.alerting.feedback import acknowledge_alert

router = APIRouter(prefix="/api", tags=["alerts"])


def _alert_out(alert: Alert, analysis: Analysis | None, article: Article | None) -> AlertOut:
    return AlertOut(
        id=alert.id,
        analysis_id=alert.analysis_id,
        config_id=alert.config_id,
        importance_score=alert.importance_score,
        status=alert.status,
        channels_sent=alert.channels_sent,
        created_at=alert.created_at,
        delivered_at=alert.delivered_at,
        acknowledged_at=alert.acknowledged_at,
        event_category=analysis.event_category if analysis else None,
        expected_direction=analysis.expected_direction if analysis else None,
        headline_summary=analysis.headline_summary if analysis else None,
        url=article.url if article else None,
    )


@router.get("/alerts", response_model=list[AlertOut])
def get_alerts(
    db: Session = Depends(get_db),
    config_id: int | None = None,
    status: str | None = None,
    since: dt.datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[AlertOut]:
    stmt = (
        select(Alert, Analysis, Article)
        .join(Analysis, Alert.analysis_id == Analysis.id)
        .outerjoin(Article, Analysis.article_id == Article.id)
    )
    if config_id:
        stmt = stmt.where(Alert.config_id == config_id)
    if status:
        stmt = stmt.where(Alert.status == status)
    if since:
        stmt = stmt.where(Alert.created_at >= since)
    rows = db.execute(stmt.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit)).all()
    return [_alert_out(al, an, art) for al, an, art in rows]


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut)
def ack_alert(alert_id: int, db: Session = Depends(get_db)) -> AlertOut:
    alert = acknowledge_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    analysis = alert.analysis
    article = analysis.article if analysis else None
    return _alert_out(alert, analysis, article)
