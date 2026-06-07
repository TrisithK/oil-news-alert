"""SSE stream of new analyses + alerts (spec §9).

Polls the DB so it sees rows produced by the separate worker process (the cross-process source
of truth), and emits a heartbeat so clients/proxies keep the connection alive.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.db.base import SessionLocal
from app.db.models import Alert, Analysis, Article

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["stream"])

_POLL_SECONDS = 1.0
_HEARTBEAT_EVERY = 10  # ticks


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _max_ids() -> tuple[int, int]:
    with SessionLocal() as db:
        return (
            db.scalar(select(func.max(Analysis.id))) or 0,
            db.scalar(select(func.max(Alert.id))) or 0,
        )


def _fetch_new(last_analysis: int, last_alert: int) -> tuple[list[dict], list[dict], int, int]:
    with SessionLocal() as db:
        analysis_rows = db.execute(
            select(Analysis, Article)
            .join(Article, Analysis.article_id == Article.id)
            .where(Analysis.id > last_analysis, Analysis.is_relevant.is_(True))
            .order_by(Analysis.id)
        ).all()
        alert_rows = db.execute(
            select(Alert, Analysis, Article)
            .join(Analysis, Alert.analysis_id == Analysis.id)
            .outerjoin(Article, Analysis.article_id == Article.id)
            .where(Alert.id > last_alert)
            .order_by(Alert.id)
        ).all()

    analyses = [
        {
            "type": "analysis",
            "id": an.id,
            "importance_score": an.importance_score,
            "event_category": an.event_category,
            "direction": an.expected_direction,
            "magnitude": an.magnitude,
            "headline_summary": an.headline_summary,
            "instruments": an.instruments_affected,
            "url": art.url,
            "created_at": an.created_at,
        }
        for an, art in analysis_rows
    ]
    alerts = [
        {
            "type": "alert",
            "id": al.id,
            "importance_score": al.importance_score,
            "event_category": an.event_category,
            "direction": an.expected_direction,
            "headline_summary": an.headline_summary,
            "url": art.url if art else None,
            "created_at": al.created_at,
        }
        for al, an, art in alert_rows
    ]
    new_last_analysis = max((an.id for an, _ in analysis_rows), default=last_analysis)
    new_last_alert = max((al.id for al, _, _ in alert_rows), default=last_alert)
    return analyses, alerts, new_last_analysis, new_last_alert


async def event_stream(is_disconnected: Callable[[], Awaitable[bool]]) -> AsyncIterator[str]:
    """The SSE body: an immediate heartbeat, then new analyses/alerts polled from the DB."""
    last_a, last_al = await asyncio.to_thread(_max_ids)
    yield _sse("heartbeat", {"ts": dt.datetime.now(dt.UTC).isoformat(), "subscribed": True})
    tick = 0
    while True:
        if await is_disconnected():
            break
        analyses, alerts, last_a, last_al = await asyncio.to_thread(_fetch_new, last_a, last_al)
        for event in analyses:
            yield _sse("analysis", event)
        for event in alerts:
            yield _sse("alert", event)
        tick += 1
        if tick % _HEARTBEAT_EVERY == 0:
            yield _sse("heartbeat", {"ts": dt.datetime.now(dt.UTC).isoformat()})
        await asyncio.sleep(_POLL_SECONDS)


@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    return StreamingResponse(
        event_stream(request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
