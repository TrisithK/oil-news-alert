"""Replay a curated Strait-of-Hormuz escalation for the interview demo (`make demo`).

Streams a few curated, escalating articles into the DB, analyzing + alerting each with a short
pause between them, so the live web UI (and Telegram, if configured) light up within seconds.
This is the canonical, highest-impact Brent driver — exactly the event a desk wants flagged the
instant it breaks (spec §2, §16).

Run the web app (`make web` or `cd frontend && npm run dev`) and open the Live Feed first to
watch it react in real time.
"""

from __future__ import annotations

import datetime as dt
import time

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import SessionLocal
from app.db.models import Article, Source
from worker.alerting.engine import process_analysis
from worker.alerting.notifier import build_default_notifiers
from worker.analyze.llm import get_llm_client
from worker.analyze.pipeline import analyze_article
from worker.seeds import seed_demo_config, seed_sources

# Distinct event categories so each fires its own alert (no cooldown suppression),
# escalating in severity — the desk sees the risk premium building in real time.
CURATED: list[dict[str, str]] = [
    {
        "title": (
            "BREAKING: Iran threatens to close the Strait of Hormuz after attacks on oil tankers"
        ),
        "body": (
            "Tehran warned it could blockade the Strait of Hormuz — the chokepoint for roughly a "
            "fifth of global seaborne crude — after overnight attacks on two tankers. Brent spiked "
            "and war-risk insurance premiums jumped."
        ),
        "url": "https://demo.local/hormuz-threat",
    },
    {
        "title": "Israel launches air strikes on Iranian military targets as conflict escalates",
        "body": (
            "Israeli jets struck Iranian targets overnight, sharply raising the oil risk premium. "
            "Traders moved to price in a sustained Middle East supply threat to Brent and gasoil."
        ),
        "url": "https://demo.local/strikes-escalate",
    },
    {
        "title": "OPEC+ signals emergency output response as Middle East oil supply risk spikes",
        "body": (
            "OPEC+ delegates discussed an emergency output response — potentially deeper cuts to "
            "stabilize the market — as the regional crisis threatened crude flows. "
            "Brent extended gains."
        ),
        "url": "https://demo.local/opec-emergency",
    },
]


def _demo_source(session) -> Source:
    src = session.execute(select(Source).where(Source.name == "Demo Replay")).scalar_one_or_none()
    if src is None:
        src = Source(
            name="Demo Replay",
            kind="rss",
            url="https://demo.local",
            reliability_tier="wire",
            poll_interval_sec=600,
            enabled=True,
        )
        session.add(src)
        session.commit()
    return src


def main() -> None:
    setup_logging()
    llm = get_llm_client(settings)
    notifiers = build_default_notifiers(settings)

    with SessionLocal() as session:
        seed_sources(session)
        seed_demo_config(session)
        source = _demo_source(session)

        print("\n=== Replaying Strait-of-Hormuz escalation — watch the Live Feed light up ===\n")
        for i, item in enumerate(CURATED, start=1):
            now = dt.datetime.now(dt.UTC)
            stamp = now.strftime("%H%M%S")
            article = Article(
                source_id=source.id,
                url=f"{item['url']}?t={stamp}",
                title=item["title"],
                body=item["body"],
                content_hash=f"demo-{stamp}-{i}",
                published_at=now,
                language="English",
                source_country="Demo",
            )
            session.add(article)
            session.commit()
            session.refresh(article)

            analysis = analyze_article(session, llm, article)
            alerts = process_analysis(session, analysis, notifiers=notifiers)
            print(
                f"[{i}/{len(CURATED)}] {item['title'][:64]}…\n"
                f"        -> {analysis.event_category} / {analysis.expected_direction} / "
                f"score {analysis.importance_score:.0f} / {len(alerts)} alert(s) fired\n"
            )
            time.sleep(3)

    print("=== Done. Open the Live Feed and Alerts pages to review. ===\n")


if __name__ == "__main__":
    main()
