"""Seed the source rows. Idempotent: re-running upserts by source name."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Source

log = logging.getLogger(__name__)

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


def main() -> None:
    from app.core.logging import setup_logging
    from app.db.base import SessionLocal

    setup_logging()
    with SessionLocal() as session:
        seed_sources(session)


if __name__ == "__main__":
    main()
