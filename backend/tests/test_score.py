from __future__ import annotations

from app.core.taxonomy import EventCategory, Magnitude
from worker.analyze.score import compute_importance, importance_breakdown


def test_known_maximal_inputs() -> None:
    # 100 * (0.35*0.90 + 0.20*1.0 + 0.15*1.0 + 0.15*1.0 + 0.15*1.0) = 96.5
    score = compute_importance(
        category=EventCategory.OPEC_SUPPLY,
        magnitude=Magnitude.HIGH,
        confidence=1.0,
        source_tier="wire",
        novelty=1.0,
    )
    assert score == 96.5


def test_scheduled_surprise_scales_score() -> None:
    base = compute_importance(
        category=EventCategory.INVENTORY,
        magnitude=Magnitude.MEDIUM,
        confidence=0.8,
        source_tier="wire",
    )
    full_surprise = compute_importance(
        category=EventCategory.INVENTORY,
        magnitude=Magnitude.MEDIUM,
        confidence=0.8,
        source_tier="wire",
        is_scheduled_data=True,
        surprise_factor=1.0,
    )
    no_surprise = compute_importance(
        category=EventCategory.INVENTORY,
        magnitude=Magnitude.MEDIUM,
        confidence=0.8,
        source_tier="wire",
        is_scheduled_data=True,
        surprise_factor=0.0,
    )
    assert full_surprise == base
    assert no_surprise == 0.0


def test_clamps_and_bounds() -> None:
    score = compute_importance(
        category=EventCategory.OPEC_SUPPLY,
        magnitude=Magnitude.HIGH,
        confidence=5.0,  # clamped to 1.0
        source_tier="unknown-tier",  # falls back to aggregator weight
        novelty=-3.0,  # clamped to 0.0
    )
    assert 0.0 <= score <= 100.0


def test_breakdown_exposes_components() -> None:
    breakdown = importance_breakdown(
        category=EventCategory.GEOPOLITICS,
        magnitude=Magnitude.HIGH,
        confidence=0.7,
        source_tier="reputable",
    )
    assert set(breakdown) >= {
        "category_weight",
        "magnitude",
        "confidence",
        "source_tier",
        "novelty",
        "importance_score",
    }
    assert breakdown["category_weight"] == 0.85
