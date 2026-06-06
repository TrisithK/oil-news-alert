"""One-shot analysis entrypoint: `python -m worker.run_analyze` (used by `make analyze`).

Analyzes ingested articles that haven't been analyzed yet. Uses the real Anthropic client when
ANTHROPIC_API_KEY is set, otherwise the offline heuristic client (no API spend).
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import SessionLocal
from worker.analyze.llm import get_llm_client
from worker.analyze.pipeline import run_analyze_once


def main() -> None:
    setup_logging()
    llm = get_llm_client(settings)
    with SessionLocal() as session:
        result = run_analyze_once(session, llm, limit=settings.max_items_per_cycle)
    print(result)


if __name__ == "__main__":
    main()
