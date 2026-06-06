"""One-shot ingest entrypoint: `python -m worker.run_ingest` (used by `make ingest`)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.db.base import SessionLocal
from app.db.models import Source
from worker.ingest.client import allow_url
from worker.ingest.eia import EIA_WEEKLY_STOCKS_URL
from worker.ingest.gdelt import GDELT_DOC_URL
from worker.ingest.service import run_ingest_once
from worker.seeds import seed_sources

log = logging.getLogger(__name__)


def register_allowlist(session: Session) -> None:
    """Allowlist only the hosts we intend to fetch from (outbound guardrail, §5)."""
    allow_url(GDELT_DOC_URL)
    allow_url(EIA_WEEKLY_STOCKS_URL)
    for source in session.execute(select(Source)).scalars():
        allow_url(source.url)


def main() -> None:
    setup_logging()
    with SessionLocal() as session:
        seed_sources(session)
        register_allowlist(session)
        result = run_ingest_once(session)
    print(result)


if __name__ == "__main__":
    main()
