"""SQLAlchemy models — the full Section 8 data model.

Categorical fields (kind, reliability_tier, direction, magnitude, status, label, ...) are
stored as plain strings and validated in code via the enums in ``app.core.taxonomy`` /
Pydantic schemas, rather than Postgres ENUM types — this keeps migrations simple and the
taxonomy editable without DDL.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    configs: Mapped[list[Config]] = relationship(back_populates="user")
    feedback: Mapped[list[Feedback]] = relationship(back_populates="user")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))  # gdelt | rss | api
    url: Mapped[str | None] = mapped_column(Text)
    reliability_tier: Mapped[str] = mapped_column(
        String(20), default="reputable"
    )  # wire | reputable | aggregator | blog_social
    poll_interval_sec: Mapped[int] = mapped_column(default=600)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    articles: Mapped[list[Article]] = relationship(back_populates="source")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    language: Mapped[str | None] = mapped_column(String(20))
    source_country: Mapped[str | None] = mapped_column(String(100))
    tone: Mapped[float | None] = mapped_column(Float)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    raw_json: Mapped[dict | None] = mapped_column(JSONB)

    source: Mapped[Source | None] = relationship(back_populates="articles")
    analyses: Mapped[list[Analysis]] = relationship(back_populates="article")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), index=True
    )
    model_triage: Mapped[str | None] = mapped_column(String(100))
    model_extract: Mapped[str | None] = mapped_column(String(100))
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    event_category: Mapped[str | None] = mapped_column(String(50))
    instruments_affected: Mapped[list | None] = mapped_column(JSONB)
    # bullish | bearish | neutral | unclear
    expected_direction: Mapped[str | None] = mapped_column(String(20))
    magnitude: Mapped[str | None] = mapped_column(String(20))  # low | medium | high
    confidence: Mapped[float | None] = mapped_column(Float)
    # immediate | intraday | days | structural
    time_horizon: Mapped[str | None] = mapped_column(String(20))
    novelty: Mapped[float | None] = mapped_column(Float)
    importance_score: Mapped[float | None] = mapped_column(Float)
    rationale: Mapped[str | None] = mapped_column(Text)
    headline_summary: Mapped[str | None] = mapped_column(Text)
    key_entities: Mapped[list | None] = mapped_column(JSONB)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    article: Mapped[Article] = relationship(back_populates="analyses")
    alerts: Mapped[list[Alert]] = relationship(back_populates="analysis")

    __table_args__ = (Index("ix_analyses_importance_created", "importance_score", "created_at"),)


class Config(Base):
    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="default")
    min_importance: Mapped[float] = mapped_column(Float, default=60.0)
    instruments: Mapped[list | None] = mapped_column(JSONB)
    categories: Mapped[list | None] = mapped_column(JSONB)
    keywords: Mapped[list | None] = mapped_column(JSONB)
    channels: Mapped[dict | None] = mapped_column(JSONB)  # {telegram_chat_id, email, in_app}
    quiet_hours: Mapped[dict | None] = mapped_column(JSONB)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="configs")
    alerts: Mapped[list[Alert]] = relationship(back_populates="config")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    config_id: Mapped[int] = mapped_column(ForeignKey("configs.id", ondelete="CASCADE"))
    importance_score: Mapped[float | None] = mapped_column(Float)
    channels_sent: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|sent|failed
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    delivered_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    analysis: Mapped[Analysis] = relationship(back_populates="alerts")
    config: Mapped[Config] = relationship(back_populates="alerts")
    feedback: Mapped[list[Feedback]] = relationship(back_populates="alert")

    __table_args__ = (Index("ix_alerts_config_created", "config_id", "created_at"),)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    label: Mapped[str] = mapped_column(String(20))  # useful | noise | missed
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    alert: Mapped[Alert] = relationship(back_populates="feedback")
    user: Mapped[User | None] = relationship(back_populates="feedback")


class EventCalendar(Base):
    __tablename__ = "event_calendar"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    scheduled_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    consensus: Mapped[float | None] = mapped_column(Float)
    actual: Mapped[float | None] = mapped_column(Float)
