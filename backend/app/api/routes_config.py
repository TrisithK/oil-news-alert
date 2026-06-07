"""Read / upsert the trader's config (watchlist + thresholds + channels)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import Config, User
from app.schemas.api import ConfigIn, ConfigOut

router = APIRouter(prefix="/api", tags=["config"])


def _config_out(config: Config) -> ConfigOut:
    return ConfigOut(
        id=config.id,
        user_id=config.user_id,
        name=config.name,
        min_importance=config.min_importance,
        instruments=config.instruments,
        categories=config.categories,
        keywords=config.keywords,
        channels=config.channels,
        quiet_hours=config.quiet_hours,
        enabled=config.enabled,
    )


@router.get("/config", response_model=ConfigOut)
def get_config(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ConfigOut:
    config = db.execute(
        select(Config).where(Config.user_id == user.id, Config.name == "default")
    ).scalar_one_or_none()
    if config is None:
        config = Config(
            user_id=user.id, name="default", min_importance=60.0, channels={"in_app": True}
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return _config_out(config)


@router.put("/config", response_model=ConfigOut)
def put_config(
    payload: ConfigIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConfigOut:
    config = db.execute(
        select(Config).where(Config.user_id == user.id, Config.name == payload.name)
    ).scalar_one_or_none()
    if config is None:
        config = Config(user_id=user.id, name=payload.name)
        db.add(config)
    config.min_importance = payload.min_importance
    config.instruments = payload.instruments
    config.categories = payload.categories
    config.keywords = payload.keywords
    config.channels = payload.channels
    config.quiet_hours = payload.quiet_hours
    config.enabled = payload.enabled
    db.commit()
    db.refresh(config)
    return _config_out(config)
