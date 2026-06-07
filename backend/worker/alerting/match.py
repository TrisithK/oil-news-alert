"""Per-trader config matching (spec §7): threshold, instruments, categories, keywords, quiet hours.

A None/empty filter means "don't filter on this" — e.g. no instruments listed = all instruments.
"""

from __future__ import annotations

import datetime as dt
import logging
from zoneinfo import ZoneInfo

from app.db.models import Analysis, Config

log = logging.getLogger(__name__)


def config_matches(config: Config, analysis: Analysis) -> bool:
    """True if the analysis clears this config's threshold and filters (quiet hours excluded)."""
    if (analysis.importance_score or 0.0) < (config.min_importance or 0.0):
        return False

    instruments = config.instruments or []
    if instruments and not set(analysis.instruments_affected or []) & set(instruments):
        return False

    categories = config.categories or []
    if categories and analysis.event_category not in categories:
        return False

    keywords = config.keywords or []
    if keywords:
        haystack = " ".join(
            part
            for part in (
                analysis.headline_summary,
                analysis.rationale,
                " ".join(analysis.key_entities or []),
            )
            if part
        ).lower()
        if not any(kw.lower() in haystack for kw in keywords):
            return False

    return True


def in_quiet_hours(config: Config, now: dt.datetime) -> bool:
    """True if ``now`` falls within the config's quiet-hours window (handles overnight wrap)."""
    quiet = config.quiet_hours or {}
    start, end = quiet.get("start"), quiet.get("end")
    if not start or not end:
        return False
    try:
        zone = ZoneInfo(quiet.get("tz", "UTC"))
    except Exception:  # noqa: BLE001 - bad tz string falls back to UTC
        zone = ZoneInfo("UTC")

    local = now.astimezone(zone)
    current = local.hour * 60 + local.minute
    try:
        sh, sm = (int(x) for x in start.split(":"))
        eh, em = (int(x) for x in end.split(":"))
    except ValueError:
        return False
    start_min, end_min = sh * 60 + sm, eh * 60 + em
    if start_min == end_min:
        return False
    if start_min < end_min:
        return start_min <= current < end_min
    return current >= start_min or current < end_min  # overnight window
