from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, Analysis, Article, Config, Source, User


def _seed_relevant(
    db_session: Session,
    *,
    importance: float = 85.0,
    category: str = "geopolitics_conflict",
    url: str = "https://x.com/a",
    chash: str = "h1",
) -> tuple[Source, Article, Analysis]:
    src = db_session.execute(select(Source).where(Source.name == "wire")).scalar_one_or_none()
    if src is None:
        src = Source(
            name="wire",
            kind="rss",
            url="https://x.com",
            reliability_tier="wire",
            poll_interval_sec=600,
        )
        db_session.add(src)
        db_session.commit()
    article = Article(source_id=src.id, url=url, title="Israel strikes Iran", content_hash=chash)
    db_session.add(article)
    db_session.commit()
    analysis = Analysis(
        article_id=article.id,
        is_relevant=True,
        event_category=category,
        instruments_affected=["BRENT"],
        expected_direction="bullish",
        magnitude="high",
        confidence=0.8,
        time_horizon="immediate",
        novelty=1.0,
        importance_score=importance,
        rationale="Risk premium rises",
        headline_summary="Israel strikes Iran",
        key_entities=["Iran"],
        model_triage="heuristic-mock",
        model_extract="heuristic-mock",
    )
    db_session.add(analysis)
    db_session.commit()
    return src, article, analysis


def test_requires_bearer_token(client: TestClient) -> None:
    assert client.get("/api/feed").status_code == 401


def test_feed_list_and_detail(api_client: TestClient, db_session: Session) -> None:
    _, _, analysis = _seed_relevant(db_session)

    resp = api_client.get("/api/feed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["id"] == analysis.id for item in body["items"])

    detail = api_client.get(f"/api/feed/{analysis.id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["event_category"] == "geopolitics_conflict"
    assert payload["score_breakdown"]["importance_score"] >= 0
    assert payload["model_extract"] == "heuristic-mock"


def test_feed_filters(api_client: TestClient, db_session: Session) -> None:
    _seed_relevant(
        db_session, importance=85, category="geopolitics_conflict", url="https://x/1", chash="c1"
    )
    _seed_relevant(
        db_session, importance=40, category="macro_monetary", url="https://x/2", chash="c2"
    )

    high = api_client.get("/api/feed", params={"min_importance": 70}).json()["items"]
    cats = {item["event_category"] for item in high}
    assert "geopolitics_conflict" in cats
    assert "macro_monetary" not in cats

    macro = api_client.get("/api/feed", params={"category": "macro_monetary", "min_importance": 0})
    assert all(it["event_category"] == "macro_monetary" for it in macro.json()["items"])


def test_config_round_trip(api_client: TestClient) -> None:
    assert api_client.get("/api/config").status_code == 200
    payload = {
        "name": "default",
        "min_importance": 82,
        "instruments": ["BRENT"],
        "categories": None,
        "keywords": ["hormuz"],
        "channels": {"in_app": True},
        "quiet_hours": None,
        "enabled": True,
    }
    put = api_client.put("/api/config", json=payload)
    assert put.status_code == 200
    assert put.json()["min_importance"] == 82

    again = api_client.get("/api/config").json()
    assert again["min_importance"] == 82
    assert again["keywords"] == ["hormuz"]


def test_sources_list_and_patch(api_client: TestClient, db_session: Session) -> None:
    src = Source(
        name="OilPrice",
        kind="rss",
        url="https://o",
        reliability_tier="aggregator",
        poll_interval_sec=900,
    )
    db_session.add(src)
    db_session.commit()

    listing = api_client.get("/api/sources")
    assert listing.status_code == 200
    assert any(s["name"] == "OilPrice" for s in listing.json())

    patched = api_client.patch(
        f"/api/sources/{src.id}", json={"enabled": False, "poll_interval_sec": 1200}
    )
    assert patched.status_code == 200
    assert patched.json()["enabled"] is False
    assert patched.json()["poll_interval_sec"] == 1200


def test_alerts_ack_and_feedback(api_client: TestClient, db_session: Session) -> None:
    _, _, analysis = _seed_relevant(db_session)
    user = User(email="trader@desk", name="Trader")
    db_session.add(user)
    db_session.flush()
    config = Config(user_id=user.id, name="watch", min_importance=70.0, channels={"in_app": True})
    db_session.add(config)
    db_session.commit()
    alert = Alert(
        analysis_id=analysis.id,
        config_id=config.id,
        importance_score=analysis.importance_score,
        status="sent",
        channels_sent={"in_app": True},
    )
    db_session.add(alert)
    db_session.commit()

    assert any(a["id"] == alert.id for a in api_client.get("/api/alerts").json())

    ack = api_client.post(f"/api/alerts/{alert.id}/ack")
    assert ack.status_code == 200
    assert ack.json()["acknowledged_at"] is not None

    good = api_client.post(
        "/api/feedback", json={"alert_id": alert.id, "label": "useful", "note": "good"}
    )
    assert good.status_code == 201
    assert good.json()["label"] == "useful"

    bad = api_client.post("/api/feedback", json={"alert_id": alert.id, "label": "bogus"})
    assert bad.status_code == 400


def test_stats(api_client: TestClient, db_session: Session) -> None:
    _seed_relevant(db_session)
    stats = api_client.get("/api/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["relevant_analyses"] >= 1
    assert "geopolitics_conflict" in body["by_category"]


def test_stream_emits_heartbeat() -> None:
    import asyncio

    from app.api.routes_stream import event_stream

    async def _disconnected() -> bool:
        return True  # break the loop after the initial heartbeat

    async def _collect() -> list[str]:
        return [chunk async for chunk in event_stream(_disconnected)]

    chunks = asyncio.run(_collect())
    assert any("event: heartbeat" in chunk for chunk in chunks)
