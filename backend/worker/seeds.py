"""Seed the source rows. Idempotent: re-running upserts by source name."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Config, Source, User

log = logging.getLogger(__name__)

DEMO_USER_EMAIL = "demo@oildesk.example"

# (name, kind, url, reliability_tier, poll_interval_sec)
SEED_SOURCES: list[tuple[str, str, str, str, int]] = [
    ("GDELT DOC", "gdelt", "https://api.gdeltproject.org/api/v2/doc/doc", "aggregator", 600),
    ("OilPrice.com", "rss", "https://oilprice.com/rss/main", "aggregator", 900),
    (
        "CNBC Energy",
        "rss",
        "https://www.cnbc.com/id/19836768/device/rss/rss.html",
        "reputable",
        900,
    ),
    (
        "Hellenic Shipping News",
        "rss",
        "https://www.hellenicshippingnews.com/feed/",
        "reputable",
        900,
    ),
    ("Rigzone", "rss", "https://www.rigzone.com/news/rss/rigzone_latest.aspx", "reputable", 900),
    (
        "EIA Weekly Petroleum",
        "api",
        "https://api.eia.gov/v2/petroleum/stoc/wstk/data/",
        "wire",
        3600,
    ),
]


def seed_sources(session: Session) -> int:
    """Insert any missing sources; update url/tier/interval on existing ones."""
    created = 0
    for name, kind, url, tier, interval in SEED_SOURCES:
        existing = session.execute(select(Source).where(Source.name == name)).scalar_one_or_none()
        if existing is not None:
            existing.kind = kind
            existing.url = url
            existing.reliability_tier = tier
            existing.poll_interval_sec = interval
            continue
        session.add(
            Source(
                name=name,
                kind=kind,
                url=url,
                reliability_tier=tier,
                poll_interval_sec=interval,
                enabled=True,
            )
        )
        created += 1
    session.commit()
    log.info("Seeded sources (created=%d, total=%d)", created, len(SEED_SOURCES))
    return created


def _filled_channels(existing: dict | None) -> dict:
    """Default channels, filling Telegram/email from settings only when not already set.

    This makes the system turnkey: drop TELEGRAM_DEFAULT_CHAT_ID / ALERT_FROM_EMAIL into .env and
    re-run, and the default config picks them up — without clobbering values a trader set in the UI.
    """
    channels = dict(existing or {})
    channels.setdefault("in_app", True)
    if settings.telegram_default_chat_id and not channels.get("telegram_chat_id"):
        channels["telegram_chat_id"] = settings.telegram_default_chat_id
    if settings.alert_from_email and not channels.get("email"):
        channels["email"] = settings.alert_from_email
    return channels


def seed_demo_config(session: Session) -> None:
    """Ensure a demo trader + a default alert config exist (idempotent)."""
    user = session.execute(select(User).where(User.email == DEMO_USER_EMAIL)).scalar_one_or_none()
    if user is None:
        user = User(email=DEMO_USER_EMAIL, name="Demo Trader", role="trader")
        session.add(user)
        session.flush()

    existing = session.execute(
        select(Config).where(Config.user_id == user.id, Config.name == "default")
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            Config(
                user_id=user.id,
                name="default",
                min_importance=70.0,
                instruments=None,  # all instruments
                categories=None,  # all categories
                keywords=None,
                channels=_filled_channels(None),
                quiet_hours=None,
                enabled=True,
            )
        )
    else:
        existing.channels = _filled_channels(existing.channels)
    session.commit()
    log.info("Seeded demo user + default config")


def main() -> None:
    from app.core.logging import setup_logging
    from app.db.base import SessionLocal

    setup_logging()
    with SessionLocal() as session:
        seed_sources(session)
        seed_demo_config(session)


if __name__ == "__main__":
    main()
