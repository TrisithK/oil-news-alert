"""Stage 4 — deterministic, explainable importance score (spec §6).

Models suggest; the formula decides. Every score decomposes into the same auditable terms,
which the UI surfaces as "Why this score".
"""

from __future__ import annotations

from app.core.taxonomy import (
    MAGNITUDE_MAP,
    SOURCE_TIER_WEIGHT,
    EventCategory,
    Magnitude,
    category_base_weight,
)

# Weights for the linear blend; sum to 1.0.
W_CATEGORY = 0.35
W_MAGNITUDE = 0.20
W_CONFIDENCE = 0.15
W_SOURCE_TIER = 0.15
W_NOVELTY = 0.15


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def importance_breakdown(
    *,
    category: EventCategory,
    magnitude: Magnitude,
    confidence: float,
    source_tier: str,
    novelty: float = 1.0,
    is_scheduled_data: bool = False,
    surprise_factor: float = 1.0,
) -> dict[str, float]:
    """Return each component's contribution plus the final score (0–100)."""
    base = category_base_weight(category)
    mag = MAGNITUDE_MAP.get(magnitude, 0.66)
    conf = _clamp01(confidence)
    tier = SOURCE_TIER_WEIGHT.get(source_tier, SOURCE_TIER_WEIGHT["aggregator"])
    nov = _clamp01(novelty)

    raw = (
        W_CATEGORY * base
        + W_MAGNITUDE * mag
        + W_CONFIDENCE * conf
        + W_SOURCE_TIER * tier
        + W_NOVELTY * nov
    )
    surprise = _clamp01(surprise_factor) if is_scheduled_data else 1.0
    score = round(_clamp01(raw * surprise) * 100.0, 1)

    return {
        "category_weight": round(base, 3),
        "magnitude": round(mag, 3),
        "confidence": round(conf, 3),
        "source_tier": round(tier, 3),
        "novelty": round(nov, 3),
        "surprise_factor": round(surprise, 3),
        "importance_score": score,
    }


def compute_importance(
    *,
    category: EventCategory,
    magnitude: Magnitude,
    confidence: float,
    source_tier: str,
    novelty: float = 1.0,
    is_scheduled_data: bool = False,
    surprise_factor: float = 1.0,
) -> float:
    return importance_breakdown(
        category=category,
        magnitude=magnitude,
        confidence=confidence,
        source_tier=source_tier,
        novelty=novelty,
        is_scheduled_data=is_scheduled_data,
        surprise_factor=surprise_factor,
    )["importance_score"]
