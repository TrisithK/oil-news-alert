"""Feedback + acknowledgement write paths (spec §7). These feed the eval harness and future
weight tuning, and are exposed over the API in Phase 4."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, Feedback

FEEDBACK_LABELS = frozenset({"useful", "noise", "missed"})


def record_feedback(
    session: Session,
    *,
    alert_id: int,
    label: str,
    user_id: int | None = None,
    note: str | None = None,
) -> Feedback:
    if label not in FEEDBACK_LABELS:
        raise ValueError(
            f"invalid feedback label: {label!r} (expected one of {sorted(FEEDBACK_LABELS)})"
        )
    feedback = Feedback(alert_id=alert_id, user_id=user_id, label=label, note=note)
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return feedback


def acknowledge_alert(
    session: Session, alert_id: int, *, now: dt.datetime | None = None
) -> Alert | None:
    alert = session.execute(select(Alert).where(Alert.id == alert_id)).scalar_one_or_none()
    if alert is None:
        return None
    alert.acknowledged_at = now or dt.datetime.now(dt.UTC)
    session.commit()
    session.refresh(alert)
    return alert
