"""Ingestion orchestration: fetch per source, normalize, dedup, persist.

Idempotent (§5): the content-hash UNIQUE constraint is the final guard, the pre-insert
``is_duplicate`` check avoids most conflicts, and a per-row savepoint absorbs the rare race
so one duplicate never aborts the whole cycle.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Article, Source
from worker.ingest.dedup import is_duplicate
from worker.ingest.eia import fetch_eia_weekly_crude
from worker.ingest.gdelt import fetch_gdelt
from worker.ingest.normalize import NormalizedArticle
from worker.ingest.rss import fetch_rss

log = logging.getLogger(__name__)


def _fetch_for_source(source: Source) -> list[NormalizedArticle]:
    if source.kind == "gdelt":
        # Window comfortably overlaps the poll interval AND GDELT's ~15-min batch cadence,
        # so we never gap between cycles. Idempotent dedup absorbs the overlap (§5).
        window = max(source.poll_interval_sec // 60 * 2, 75)
        return fetch_gdelt(timespan_minutes=window, max_records=settings.max_items_per_cycle)
    if source.kind == "rss":
        return fetch_rss(source.url) if source.url else []
    if source.kind == "api":
        # EIA is the only `api` source in the MVP seed.
        return fetch_eia_weekly_crude(settings.eia_api_key)
    log.warning("Unknown source kind: %s", source.kind)
    return []


def store_articles(
    session: Session, items: Sequence[NormalizedArticle], source_id: int
) -> tuple[int, int]:
    """Insert new articles, skipping duplicates. Returns (inserted, skipped)."""
    inserted = skipped = 0
    seen_in_batch: set[str] = set()
    for item in items:
        chash = item.content_hash
        if chash in seen_in_batch:
            skipped += 1
            continue
        seen_in_batch.add(chash)
        if is_duplicate(session, content_hash=chash, url=item.url):
            skipped += 1
            continue
        article = Article(
            source_id=source_id,
            external_id=item.external_id,
            url=item.url,
            title=item.title,
            body=item.body,
            published_at=item.published_at,
            language=item.language,
            source_country=item.source_country,
            tone=item.tone,
            content_hash=chash,
            raw_json=item.raw,
        )
        savepoint = session.begin_nested()
        session.add(article)
        try:
            savepoint.commit()
            inserted += 1
        except IntegrityError:
            savepoint.rollback()
            skipped += 1
    session.commit()
    return inserted, skipped


def ingest_source(session: Session, source: Source) -> tuple[int, int]:
    try:
        items = _fetch_for_source(source)
    except Exception:  # noqa: BLE001 — one bad source must not kill the cycle
        log.exception("Fetch failed for source %s (%s)", source.name, source.kind)
        return (0, 0)
    capped = list(items)[: settings.max_items_per_cycle]
    inserted, skipped = store_articles(session, capped, source.id)
    log.info(
        "source=%-24s kind=%-5s fetched=%-3d inserted=%-3d skipped=%-3d",
        source.name,
        source.kind,
        len(items),
        inserted,
        skipped,
    )
    return inserted, skipped


def run_ingest_once(session: Session) -> dict[str, int]:
    sources = (
        session.execute(select(Source).where(Source.enabled.is_(True)).order_by(Source.id))
        .scalars()
        .all()
    )
    total_inserted = total_skipped = 0
    for source in sources:
        ins, skip = ingest_source(session, source)
        total_inserted += ins
        total_skipped += skip
    result = {"sources": len(sources), "inserted": total_inserted, "skipped": total_skipped}
    log.info("Ingest cycle complete: %s", result)
    return result
