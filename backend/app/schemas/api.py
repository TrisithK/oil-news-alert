"""Pydantic request/response models for the API (typed responses + OpenAPI)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class FeedItem(BaseModel):
    id: int
    article_id: int
    created_at: dt.datetime
    importance_score: float | None
    event_category: str | None
    expected_direction: str | None
    magnitude: str | None
    confidence: float | None
    time_horizon: str | None
    instruments_affected: list[str] | None
    headline_summary: str | None
    rationale: str | None
    # Article context
    title: str
    url: str
    source_name: str | None
    source_tier: str | None
    published_at: dt.datetime | None


class FeedPage(BaseModel):
    items: list[FeedItem]
    total: int
    limit: int
    offset: int


class ScoreBreakdown(BaseModel):
    category_weight: float
    magnitude: float
    confidence: float
    source_tier: float
    novelty: float
    surprise_factor: float
    importance_score: float


class FeedDetail(FeedItem):
    # The model_triage/model_extract fields shadow Pydantic's protected "model_" namespace.
    model_config = ConfigDict(protected_namespaces=())

    novelty: float | None
    key_entities: list[str] | None
    model_triage: str | None
    model_extract: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    score_breakdown: ScoreBreakdown


class AlertOut(BaseModel):
    id: int
    analysis_id: int
    config_id: int
    importance_score: float | None
    status: str
    channels_sent: dict | None
    created_at: dt.datetime
    delivered_at: dt.datetime | None
    acknowledged_at: dt.datetime | None
    event_category: str | None
    expected_direction: str | None
    headline_summary: str | None
    url: str | None


class ConfigIn(BaseModel):
    name: str = "default"
    min_importance: float = Field(default=60.0, ge=0.0, le=100.0)
    instruments: list[str] | None = None
    categories: list[str] | None = None
    keywords: list[str] | None = None
    channels: dict | None = None
    quiet_hours: dict | None = None
    enabled: bool = True


class ConfigOut(ConfigIn):
    id: int
    user_id: int


class SourceOut(BaseModel):
    id: int
    name: str
    kind: str
    url: str | None
    reliability_tier: str
    poll_interval_sec: int
    enabled: bool
    last_fetched_at: dt.datetime | None = None


class SourcePatch(BaseModel):
    enabled: bool | None = None
    poll_interval_sec: int | None = Field(default=None, ge=30)


class FeedbackIn(BaseModel):
    alert_id: int
    label: str  # useful | noise | missed
    note: str | None = None


class FeedbackOut(BaseModel):
    id: int
    alert_id: int
    label: str
    note: str | None
    created_at: dt.datetime


class Stats(BaseModel):
    total_articles: int
    total_analyses: int
    relevant_analyses: int
    total_alerts: int
    by_category: dict[str, int]
    by_direction: dict[str, int]
    avg_importance: float | None
    feedback_counts: dict[str, int]
    feedback_useful_ratio: float | None
    avg_time_to_alert_sec: float | None
    total_prompt_tokens: int
    total_completion_tokens: int
