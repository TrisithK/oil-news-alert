from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.db.models import Alert, Analysis, Article, Config, Source, User
from worker.alerting.feedback import acknowledge_alert, record_feedback


def _make_alert(db_session: Session) -> Alert:
    src = Source(
        name="s", kind="rss", url="https://x", reliability_tier="wire", poll_interval_sec=600
    )
    db_session.add(src)
    db_session.commit()
    article = Article(source_id=src.id, url="https://x/a", title="t", content_hash="h")
    db_session.add(article)
    db_session.commit()
    analysis = Analysis(article_id=article.id, is_relevant=True, importance_score=90.0, novelty=1.0)
    db_session.add(analysis)
    db_session.commit()
    user = User(email="u@u")
    db_session.add(user)
    db_session.flush()
    config = Config(user_id=user.id, name="default", min_importance=70.0)
    db_session.add(config)
    db_session.commit()
    alert = Alert(
        analysis_id=analysis.id,
        config_id=config.id,
        importance_score=90.0,
        status="sent",
        channels_sent={"in_app": True},
    )
    db_session.add(alert)
    db_session.commit()
    return alert


def test_record_feedback_and_acknowledge(db_session: Session) -> None:
    alert = _make_alert(db_session)
    feedback = record_feedback(db_session, alert_id=alert.id, label="useful", note="great call")
    assert feedback.id is not None
    assert feedback.label == "useful"

    acked = acknowledge_alert(db_session, alert.id)
    assert acked is not None
    assert acked.acknowledged_at is not None


def test_invalid_label_rejected(db_session: Session) -> None:
    with pytest.raises(ValueError):
        record_feedback(db_session, alert_id=1, label="bogus")


def test_acknowledge_missing_alert(db_session: Session) -> None:
    assert acknowledge_alert(db_session, 999_999) is None
