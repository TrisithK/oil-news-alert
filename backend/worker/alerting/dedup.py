"""Event-level dedup (spec §7) — the single biggest defense against alert fatigue.

Suppresses an alert if (a) this exact analysis already alerted this config, or (b) the same
config already fired for the same event category inside the cooldown window. Embedding-based
story clustering is the documented scale path; category-within-cooldown is the MVP proxy.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, Analysis, Config


def recently_alerted(
    session: Session,
    config: Config,
    analysis: Analysis,
    cooldown_sec: int,
    now: dt.datetime,
) -> bool:
    already = session.execute(
        select(Alert.id)
        .where(Alert.analysis_id == analysis.id, Alert.config_id == config.id)
        .limit(1)
    ).first()
    if already is not None:
        return True

    if not analysis.event_category:
        return False

    cutoff = now - dt.timedelta(seconds=cooldown_sec)
    same_cluster = session.execute(
        select(Alert.id)
        .join(Analysis, Alert.analysis_id == Analysis.id)
        .where(
            Alert.config_id == config.id,
            Analysis.event_category == analysis.event_category,
            Alert.created_at >= cutoff,
        )
        .limit(1)
    ).first()
    return same_cluster is not None
