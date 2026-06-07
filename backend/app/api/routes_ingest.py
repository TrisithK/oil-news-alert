"""Manual ingest+analyze+alert trigger (dev/demo only, spec §9)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from worker.alerting.engine import process_analysis
from worker.alerting.notifier import build_default_notifiers
from worker.analyze.llm import get_llm_client
from worker.analyze.pipeline import run_analyze_once
from worker.ingest.service import run_ingest_once
from worker.run_ingest import register_allowlist
from worker.seeds import seed_demo_config, seed_sources

router = APIRouter(prefix="/api", tags=["dev"])


@router.post("/ingest/run")
def ingest_run(db: Session = Depends(get_db)) -> dict:
    """Run one full ingest -> analyze -> alert cycle and return counts. Makes live calls."""
    seed_sources(db)
    seed_demo_config(db)
    register_allowlist(db)
    ingest = run_ingest_once(db)
    llm = get_llm_client(settings)
    notifiers = build_default_notifiers(settings)
    analyze = run_analyze_once(
        db,
        llm,
        limit=settings.max_items_per_cycle,
        on_analysis=lambda s, a: process_analysis(s, a, notifiers=notifiers),
    )
    return {"ingest": ingest, "analyze": analyze}
