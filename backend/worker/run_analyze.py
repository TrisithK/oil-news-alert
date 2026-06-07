"""One-shot analyze + alert entrypoint: `python -m worker.run_analyze` (used by `make analyze`).

Analyzes ingested articles that haven't been analyzed yet and fires alerts for matching configs.
Uses the real Anthropic client when ANTHROPIC_API_KEY is set, otherwise the offline heuristic
client (no API spend).
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import SessionLocal
from worker.alerting.engine import process_analysis
from worker.alerting.notifier import build_default_notifiers
from worker.analyze.llm import get_llm_client
from worker.analyze.pipeline import run_analyze_once
from worker.seeds import seed_demo_config


def main() -> None:
    setup_logging()
    llm = get_llm_client(settings)
    notifiers = build_default_notifiers(settings)
    with SessionLocal() as session:
        seed_demo_config(session)
        result = run_analyze_once(
            session,
            llm,
            limit=settings.max_items_per_cycle,
            on_analysis=lambda s, a: process_analysis(s, a, notifiers=notifiers),
        )
    print(result)


if __name__ == "__main__":
    main()
