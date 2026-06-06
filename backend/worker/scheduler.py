"""Continuous ingestion worker: `python -m worker.scheduler` (the `worker` compose service).

APScheduler runs an ingest cycle every INGEST_INTERVAL_SEC. The MVP keeps the scheduler
in-process; Celery + Redis is the scale path (§4).
"""

from __future__ import annotations

import datetime as dt
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import SessionLocal
from worker.ingest.service import run_ingest_once
from worker.run_ingest import register_allowlist
from worker.seeds import seed_sources

log = logging.getLogger(__name__)


def _cycle() -> None:
    try:
        with SessionLocal() as session:
            run_ingest_once(session)
    except Exception:
        log.exception("Ingest cycle failed")


def main() -> None:
    setup_logging()
    with SessionLocal() as session:
        seed_sources(session)
        register_allowlist(session)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _cycle,
        "interval",
        seconds=settings.ingest_interval_sec,
        next_run_time=dt.datetime.now(dt.UTC),
        id="ingest_cycle",
        max_instances=1,
        coalesce=True,
    )
    log.info("Ingestion worker started; cycle every %ss", settings.ingest_interval_sec)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Ingestion worker stopping")


if __name__ == "__main__":
    main()
