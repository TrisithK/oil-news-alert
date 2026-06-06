from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Analysis, Article, Source
from eval.run_eval import load_golden_set
from worker.analyze.llm import HeuristicLLMClient
from worker.analyze.pipeline import run_analyze_once


def _seed_articles(db_session: Session, titles: list[str]) -> None:
    src = Source(
        name="wire-test",
        kind="rss",
        url="https://x.com",
        reliability_tier="wire",
        poll_interval_sec=600,
        enabled=True,
    )
    db_session.add(src)
    db_session.commit()
    for i, title in enumerate(titles):
        db_session.add(
            Article(source_id=src.id, url=f"https://x.com/{i}", title=title, content_hash=f"h{i}")
        )
    db_session.commit()


def test_pipeline_produces_valid_or_discarded_analyses(db_session: Session) -> None:
    titles = [item["title"] for item in load_golden_set()][:20]
    _seed_articles(db_session, titles)

    counts = run_analyze_once(db_session, HeuristicLLMClient())
    assert counts["processed"] == 20

    analyses = db_session.execute(select(Analysis)).scalars().all()
    assert len(analyses) == 20  # one row per article, always

    for a in analyses:
        assert 0.0 <= (a.importance_score or 0.0) <= 100.0
        if a.is_relevant:
            # Valid structured signal persisted.
            assert a.event_category is not None
            assert a.expected_direction is not None
            assert a.importance_score and a.importance_score > 0.0
        else:
            # Filtered or discarded — must carry a logged reason.
            assert a.rationale

    # The golden headlines are oil-relevant, so most should yield signals.
    assert counts["relevant"] >= 15


def test_pipeline_is_idempotent(db_session: Session) -> None:
    titles = [item["title"] for item in load_golden_set()][:10]
    _seed_articles(db_session, titles)
    llm = HeuristicLLMClient()

    run_analyze_once(db_session, llm)
    second = run_analyze_once(db_session, llm)  # nothing new to analyze

    assert second["processed"] == 0
    assert db_session.scalar(select(func.count()).select_from(Analysis)) == 10
