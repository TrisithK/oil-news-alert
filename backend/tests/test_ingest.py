from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Article, Source
from worker.ingest.normalize import NormalizedArticle
from worker.ingest.service import store_articles
from worker.seeds import seed_sources


def _source(db_session: Session) -> Source:
    src = Source(
        name="test-gdelt",
        kind="gdelt",
        url="https://x.com",
        reliability_tier="aggregator",
        poll_interval_sec=600,
        enabled=True,
    )
    db_session.add(src)
    db_session.commit()
    return src


def _items() -> list[NormalizedArticle]:
    return [
        NormalizedArticle(url="https://x.com/1", title="OPEC+ cuts output", source_kind="gdelt"),
        NormalizedArticle(
            url="https://x.com/2", title="Hormuz tensions flare", source_kind="gdelt"
        ),
        # Exact duplicate of the first item.
        NormalizedArticle(url="https://x.com/1", title="OPEC+ cuts output", source_kind="gdelt"),
    ]


def _article_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Article)) or 0


def test_store_articles_dedups_within_a_batch(db_session: Session) -> None:
    src = _source(db_session)
    inserted, skipped = store_articles(db_session, _items(), src.id)
    assert inserted == 2
    assert skipped == 1
    assert _article_count(db_session) == 2


def test_reingest_inserts_no_duplicates(db_session: Session) -> None:
    src = _source(db_session)
    items = _items()[:2]
    store_articles(db_session, items, src.id)
    inserted, skipped = store_articles(db_session, items, src.id)  # second cycle
    assert inserted == 0
    assert skipped == 2
    assert _article_count(db_session) == 2


def test_same_url_different_headline_is_deduped(db_session: Session) -> None:
    src = _source(db_session)
    store_articles(
        db_session,
        [
            NormalizedArticle(
                url="https://x.com/story", title="Original headline", source_kind="rss"
            )
        ],
        src.id,
    )
    # A reworded copy at the same URL must not create a second article (§5 same-URL check).
    inserted, skipped = store_articles(
        db_session,
        [
            NormalizedArticle(
                url="https://x.com/story", title="Reworded headline", source_kind="rss"
            )
        ],
        src.id,
    )
    assert inserted == 0
    assert skipped == 1
    assert _article_count(db_session) == 1


def test_seed_sources_is_idempotent(db_session: Session) -> None:
    created_first = seed_sources(db_session)
    created_second = seed_sources(db_session)
    assert created_first > 0
    assert created_second == 0
    total = db_session.scalar(select(func.count()).select_from(Source))
    assert total == created_first
