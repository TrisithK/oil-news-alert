"""Alerting engine (spec §7): evaluate a new analysis against every enabled config, suppress
on quiet hours and event-level cooldown, deliver to the config's channels, and persist an Alert
row with per-channel delivery status."""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Alert, Analysis, Config
from worker.alerting.dedup import recently_alerted
from worker.alerting.match import config_matches, in_quiet_hours
from worker.alerting.notifier import (
    Notifiers,
    build_default_notifiers,
    build_event,
    format_alert_message,
)

log = logging.getLogger(__name__)


def process_analysis(
    session: Session,
    analysis: Analysis,
    *,
    notifiers: Notifiers | None = None,
    cooldown_sec: int | None = None,
    now: dt.datetime | None = None,
) -> list[Alert]:
    """Fan a relevant analysis out to matching configs; return the alerts actually created."""
    if not analysis.is_relevant:
        return []

    notifiers = notifiers or build_default_notifiers()
    cooldown = cooldown_sec if cooldown_sec is not None else settings.alert_cooldown_sec
    now = now or dt.datetime.now(dt.UTC)
    article = analysis.article

    configs = session.execute(select(Config).where(Config.enabled.is_(True))).scalars().all()
    created: list[Alert] = []
    for config in configs:
        if not config_matches(config, analysis):
            continue
        if in_quiet_hours(config, now):
            log.info(
                "alert suppressed (quiet hours): config=%s analysis=%s", config.id, analysis.id
            )
            continue
        if recently_alerted(session, config, analysis, cooldown, now):
            log.info(
                "alert suppressed (cooldown dedup): config=%s analysis=%s", config.id, analysis.id
            )
            continue

        channels = config.channels or {}
        text = format_alert_message(analysis, article)
        sent: dict[str, bool] = {}

        if channels.get("in_app", True):
            notifiers.publish_in_app(build_event(analysis, article, config))
            sent["in_app"] = True

        chat_id = channels.get("telegram_chat_id")
        if chat_id and notifiers.telegram is not None:
            sent["telegram"] = notifiers.telegram.send(text=text, target=str(chat_id))

        email = channels.get("email")
        if email and notifiers.email is not None:
            sent["email"] = notifiers.email.send(text=text, target=email)

        status = "sent" if any(sent.values()) else "failed"
        alert = Alert(
            analysis_id=analysis.id,
            config_id=config.id,
            importance_score=analysis.importance_score,
            channels_sent=sent,
            status=status,
            delivered_at=now if status == "sent" else None,
        )
        session.add(alert)
        session.commit()
        session.refresh(alert)
        created.append(alert)
        log.info(
            "alert id=%s config=%s status=%s channels=%s score=%.1f",
            alert.id,
            config.id,
            status,
            sent,
            analysis.importance_score or 0.0,
        )
    return created


def run_alerting_once(
    session: Session, notifiers: Notifiers | None = None, *, limit: int | None = None
) -> dict[str, int]:
    """Backfill pass: evaluate relevant analyses that don't have any alert row yet."""
    stmt = (
        select(Analysis)
        .where(
            Analysis.is_relevant.is_(True),
            ~exists().where(Alert.analysis_id == Analysis.id),
        )
        .order_by(Analysis.importance_score.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    analyses = session.execute(stmt).scalars().all()

    counts = {"evaluated": 0, "alerts": 0}
    for analysis in analyses:
        alerts = process_analysis(session, analysis, notifiers=notifiers)
        counts["evaluated"] += 1
        counts["alerts"] += len(alerts)
    log.info("Alerting cycle complete: %s", counts)
    return counts
