from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Config, User
from worker.seeds import DEMO_USER_EMAIL, seed_demo_config


def _default_config(db_session: Session) -> Config:
    return db_session.execute(
        select(Config)
        .join(User, Config.user_id == User.id)
        .where(User.email == DEMO_USER_EMAIL, Config.name == "default")
    ).scalar_one()


def test_seed_demo_config_fills_telegram_from_settings(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Fresh seed: no Telegram chat id configured in the (test) environment.
    seed_demo_config(db_session)
    cfg = _default_config(db_session)
    assert (cfg.channels or {}).get("telegram_chat_id") is None
    assert (cfg.channels or {}).get("in_app") is True

    # Add a chat id (as if it were dropped into .env) and re-seed: it propagates.
    monkeypatch.setattr(settings, "telegram_default_chat_id", "999111")
    seed_demo_config(db_session)
    db_session.refresh(cfg)
    assert cfg.channels["telegram_chat_id"] == "999111"

    # A different .env value must NOT clobber an already-set chat id (UI wins).
    monkeypatch.setattr(settings, "telegram_default_chat_id", "different")
    seed_demo_config(db_session)
    db_session.refresh(cfg)
    assert cfg.channels["telegram_chat_id"] == "999111"


def test_seed_demo_config_is_idempotent(db_session: Session) -> None:
    seed_demo_config(db_session)
    seed_demo_config(db_session)
    count = len(
        db_session.execute(
            select(Config)
            .join(User, Config.user_id == User.id)
            .where(User.email == DEMO_USER_EMAIL)
        )
        .scalars()
        .all()
    )
    assert count == 1
