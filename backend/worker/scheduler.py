"""Continuous worker: `python -m worker.scheduler` (the `worker` compose service).

APScheduler runs a full ingest -> analyze -> alert cycle every INGEST_INTERVAL_SEC. The MVP keeps
the scheduler in-process; Celery + Redis is the scale path (spec §4).
"""

from __future__ import annotations

import datetime as dt
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import SessionLocal
from worker.alerting.engine import process_analysis
from worker.alerting.notifier import Notifiers, build_default_notifiers
from worker.analyze.llm import LLMClient, get_llm_client
from worker.analyze.pipeline import run_analyze_once
from worker.ingest.service import run_ingest_once
from worker.run_ingest import register_allowlist
from worker.seeds import seed_demo_config, seed_sources

log = logging.getLogger(__name__)


def run_cycle(llm: LLMClient, notifiers: Notifiers) -> None:
    """One full worker cycle: ingest -> analyze -> alert."""
    try:
        with SessionLocal() as session:
            run_ingest_once(session)
            run_analyze_once(
                session,
                llm,
                limit=settings.max_items_per_cycle,
                on_analysis=lambda s, a: process_analysis(s, a, notifiers=notifiers),
            )
    except Exception:
        log.exception("Worker cycle failed")


def main() -> None:
    setup_logging()
    llm = get_llm_client(settings)
    notifiers = build_default_notifiers(settings)
    with SessionLocal() as session:
        seed_sources(session)
        seed_demo_config(session)
        register_allowlist(session)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_cycle,
        "interval",
        seconds=settings.ingest_interval_sec,
        args=[llm, notifiers],
        next_run_time=dt.datetime.now(dt.UTC),
        id="worker_cycle",
        max_instances=1,
        coalesce=True,
    )
    log.info("Worker started; ingest+analyze+alert cycle every %ss", settings.ingest_interval_sec)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Worker stopping")


if __name__ == "__main__":
    main()
