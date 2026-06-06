"""Pydantic models for LLM output. The LLM is forced to emit JSON matching ``OilSignal``;
we validate (and repair-or-discard) here so a hallucinated or malformed payload never reaches
the database (spec §6, §18)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.taxonomy import Direction, EventCategory, Instrument, Magnitude, TimeHorizon


class OilSignal(BaseModel):
    is_relevant: bool
    event_category: EventCategory
    instruments_affected: list[Instrument] = Field(default_factory=list)
    expected_direction: Direction
    magnitude: Magnitude
    confidence: float
    time_horizon: TimeHorizon
    rationale: str
    headline_summary: str
    key_entities: list[str] = Field(default_factory=list)
    is_scheduled_data: bool = False

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, value: object) -> float:
        try:
            v = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0
        return min(1.0, max(0.0, v))


class TriageResult(BaseModel):
    is_relevant: bool
    reason: str = ""
