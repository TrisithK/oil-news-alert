"""The staged analysis pipeline (spec §6): prefilter -> triage -> extract -> score -> persist.

Every article that is touched gets exactly one Analysis row — including prefilter/triage drops
and extraction discards (with the reason in ``rationale``) — so re-runs never reprocess an item
and the stats panel can account for filtered volume.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from time import perf_counter

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.db.models import Analysis, Article
from worker.analyze.llm import LLMClient
from worker.analyze.prefilter import passes_prefilter
from worker.analyze.score import compute_importance

log = logging.getLogger(__name__)


def _persist(
    session: Session,
    article: Article,
    *,
    is_relevant: bool,
    rationale: str,
    model_triage: str | None = None,
    model_extract: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> Analysis:
    analysis = Analysis(
        article_id=article.id,
        is_relevant=is_relevant,
        rationale=rationale,
        model_triage=model_triage,
        model_extract=model_extract,
        novelty=1.0,
        importance_score=0.0,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def analyze_article(session: Session, llm: LLMClient, article: Article) -> Analysis:
    t_start = perf_counter()
    title, body = article.title, article.body

    # Stage 1 — keyword prefilter (free).
    if not passes_prefilter(title, body):
        log.info("article=%s prefilter=drop", article.id)
        return _persist(session, article, is_relevant=False, rationale="prefilter: no oil keywords")

    # Stage 2 — relevance triage (cheap model).
    t2 = perf_counter()
    triage, u_triage = llm.triage(title=title, body=body)
    triage_ms = (perf_counter() - t2) * 1000
    if not triage.is_relevant:
        log.info("article=%s triage=drop (%.0fms) reason=%s", article.id, triage_ms, triage.reason)
        return _persist(
            session,
            article,
            is_relevant=False,
            rationale=f"triage: {triage.reason}",
            model_triage=llm.triage_model,
            prompt_tokens=u_triage.prompt_tokens,
            completion_tokens=u_triage.completion_tokens,
        )

    # Stage 3 — structured signal extraction (expensive model), validated/repaired/discarded.
    t3 = perf_counter()
    signal, u_extract, discard = llm.extract(title=title, body=body)
    extract_ms = (perf_counter() - t3) * 1000
    usage = u_triage + u_extract
    if signal is None:
        log.warning("article=%s extract=discard reason=%s", article.id, discard)
        return _persist(
            session,
            article,
            is_relevant=False,
            rationale=f"extraction discarded: {discard}",
            model_triage=llm.triage_model,
            model_extract=llm.extract_model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

    # Stage 4 — deterministic importance score.
    tier = article.source.reliability_tier if article.source else "aggregator"
    novelty = 1.0  # MVP: every ingested article is already deduped. Clustering is the scale path.
    importance = compute_importance(
        category=signal.event_category,
        magnitude=signal.magnitude,
        confidence=signal.confidence,
        source_tier=tier,
        novelty=novelty,
        is_scheduled_data=signal.is_scheduled_data,
    )

    analysis = Analysis(
        article_id=article.id,
        model_triage=llm.triage_model,
        model_extract=llm.extract_model,
        is_relevant=signal.is_relevant,
        event_category=signal.event_category.value,
        instruments_affected=[i.value for i in signal.instruments_affected],
        expected_direction=signal.expected_direction.value,
        magnitude=signal.magnitude.value,
        confidence=signal.confidence,
        time_horizon=signal.time_horizon.value,
        novelty=novelty,
        importance_score=importance,
        rationale=signal.rationale,
        headline_summary=signal.headline_summary,
        key_entities=signal.key_entities,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)

    total_ms = (perf_counter() - t_start) * 1000
    log.info(
        "article=%s relevant cat=%s dir=%s mag=%s score=%.1f "
        "(triage %.0fms, extract %.0fms, total %.0fms, tokens=%d/%d)",
        article.id,
        signal.event_category.value,
        signal.expected_direction.value,
        signal.magnitude.value,
        importance,
        triage_ms,
        extract_ms,
        total_ms,
        usage.prompt_tokens,
        usage.completion_tokens,
    )
    return analysis


def run_analyze_once(
    session: Session,
    llm: LLMClient,
    *,
    limit: int | None = None,
    on_analysis: Callable[[Session, Analysis], None] | None = None,
) -> dict[str, int]:
    """Analyze all articles that don't yet have an Analysis row.

    ``on_analysis`` (e.g. the alerting engine) is invoked after each analysis is persisted,
    keeping the pipeline itself decoupled from alerting.
    """
    stmt = (
        select(Article)
        .where(~exists().where(Analysis.article_id == Article.id))
        .order_by(Article.fetched_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    articles = session.execute(stmt).scalars().all()

    counts = {"processed": 0, "relevant": 0, "filtered": 0, "discarded": 0}
    for article in articles:
        analysis = analyze_article(session, llm, article)
        counts["processed"] += 1
        reason = analysis.rationale or ""
        if analysis.is_relevant:
            counts["relevant"] += 1
        elif reason.startswith(("prefilter", "triage")):
            counts["filtered"] += 1
        else:
            counts["discarded"] += 1
        if on_analysis is not None:
            try:
                on_analysis(session, analysis)
            except Exception:
                log.exception("on_analysis hook failed for analysis=%s", analysis.id)
    log.info("Analysis cycle complete: %s", counts)
    return counts
