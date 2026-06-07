from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.db.models import Analysis, Article, Config, Source, User
from worker.alerting.engine import process_analysis
from worker.alerting.notifier import Notifiers


class _Recorder:
    """Duck-typed Notifier that records sends instead of hitting the network."""

    def __init__(self) -> None:
        self.sent: list[tuple[str | None, str]] = []

    @property
    def configured(self) -> bool:
        return True

    def send(self, *, text: str, target: str | None) -> bool:
        self.sent.append((target, text))
        return True


def _make_notifiers() -> tuple[Notifiers, _Recorder, list[dict]]:
    telegram = _Recorder()
    events: list[dict] = []
    return Notifiers(telegram=telegram, email=None, publish_in_app=events.append), telegram, events


def _setup(
    db_session: Session,
    *,
    importance: float = 90.0,
    category: str = "geopolitics_conflict",
    url: str = "https://x.com/a",
    chash: str = "h1",
) -> tuple[Analysis, Config]:
    src = Source(
        name="wire", kind="rss", url="https://x.com", reliability_tier="wire", poll_interval_sec=600
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
    )
    db_session.add(analysis)
    db_session.commit()
    user = User(email="trader@desk", name="Trader")
    db_session.add(user)
    db_session.flush()
    config = Config(
        user_id=user.id,
        name="default",
        min_importance=70.0,
        channels={"in_app": True, "telegram_chat_id": "12345"},
        enabled=True,
    )
    db_session.add(config)
    db_session.commit()
    return analysis, config


def test_high_importance_triggers_in_app_and_telegram(db_session: Session) -> None:
    analysis, _ = _setup(db_session)
    notifiers, telegram, events = _make_notifiers()

    alerts = process_analysis(db_session, analysis, notifiers=notifiers)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.status == "sent"
    assert alert.channels_sent.get("in_app") is True
    assert alert.channels_sent.get("telegram") is True
    assert alert.delivered_at is not None
    assert len(telegram.sent) == 1 and telegram.sent[0][0] == "12345"
    assert len(events) == 1 and events[0]["type"] == "alert"


def test_below_threshold_no_alert(db_session: Session) -> None:
    analysis, _ = _setup(db_session, importance=50.0)
    notifiers, telegram, _ = _make_notifiers()
    assert process_analysis(db_session, analysis, notifiers=notifiers) == []
    assert telegram.sent == []


def test_quiet_hours_suppresses(db_session: Session) -> None:
    analysis, config = _setup(db_session)
    config.quiet_hours = {"start": "00:00", "end": "23:59", "tz": "UTC"}  # always quiet
    db_session.commit()
    notifiers, telegram, _ = _make_notifiers()
    now = dt.datetime.now(dt.UTC).replace(hour=12, minute=0)
    assert process_analysis(db_session, analysis, notifiers=notifiers, now=now) == []
    assert telegram.sent == []


def test_same_analysis_not_alerted_twice(db_session: Session) -> None:
    analysis, _ = _setup(db_session)
    notifiers, _, _ = _make_notifiers()
    first = process_analysis(db_session, analysis, notifiers=notifiers)
    again = process_analysis(db_session, analysis, notifiers=notifiers)
    assert len(first) == 1
    assert again == []  # same analysis + config guard


def test_event_cooldown_dedup(db_session: Session) -> None:
    analysis, config = _setup(db_session)
    notifiers, _, _ = _make_notifiers()
    now = dt.datetime.now(dt.UTC)
    first = process_analysis(db_session, analysis, notifiers=notifiers, now=now)
    assert len(first) == 1

    # A different analysis, same event category, within the cooldown window -> suppressed.
    article2 = Article(
        source_id=analysis.article.source_id,
        url="https://x.com/b",
        title="More strikes reported",
        content_hash="h2",
    )
    db_session.add(article2)
    db_session.commit()
    analysis2 = Analysis(
        article_id=article2.id,
        is_relevant=True,
        event_category="geopolitics_conflict",
        instruments_affected=["BRENT"],
        expected_direction="bullish",
        magnitude="high",
        confidence=0.8,
        time_horizon="immediate",
        novelty=1.0,
        importance_score=88.0,
        rationale="More escalation",
        headline_summary="More strikes",
        key_entities=[],
    )
    db_session.add(analysis2)
    db_session.commit()

    second = process_analysis(
        db_session, analysis2, notifiers=notifiers, now=now + dt.timedelta(minutes=5)
    )
    assert second == []


def test_not_relevant_no_alert(db_session: Session) -> None:
    analysis, _ = _setup(db_session)
    analysis.is_relevant = False
    db_session.commit()
    notifiers, _, _ = _make_notifiers()
    assert process_analysis(db_session, analysis, notifiers=notifiers) == []
