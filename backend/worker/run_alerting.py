"""One-shot alerting backfill: `python -m worker.run_alerting` (used by `make alert`).

Evaluates relevant analyses that don't have an alert row yet — handy for firing alerts over
data analyzed before alerting was wired in, and for the demo.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import SessionLocal
from worker.alerting.engine import run_alerting_once
from worker.alerting.notifier import build_default_notifiers
from worker.seeds import seed_demo_config


def main() -> None:
    setup_logging()
    notifiers = build_default_notifiers(settings)
    with SessionLocal() as session:
        seed_demo_config(session)
        result = run_alerting_once(session, notifiers, limit=settings.max_items_per_cycle)
    print(result)


if __name__ == "__main__":
    main()
