from __future__ import annotations

import pytest
from pydantic import ValidationError

from worker.analyze.schema import OilSignal

_VALID = {
    "is_relevant": True,
    "event_category": "geopolitics_conflict",
    "instruments_affected": ["BRENT", "GASOIL"],
    "expected_direction": "bullish",
    "magnitude": "high",
    "confidence": 0.8,
    "time_horizon": "immediate",
    "rationale": "Escalation raises the oil risk premium.",
    "headline_summary": "Middle East escalation, bullish Brent",
    "key_entities": ["Iran", "Israel"],
    "is_scheduled_data": False,
}


def test_valid_payload_parses() -> None:
    signal = OilSignal.model_validate(_VALID)
    assert signal.event_category.value == "geopolitics_conflict"
    assert signal.expected_direction.value == "bullish"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(1.5, 1.0), (-0.2, 0.0), ("0.42", 0.42), ("garbage", 0.0)],
)
def test_confidence_is_clamped(raw: object, expected: float) -> None:
    signal = OilSignal.model_validate({**_VALID, "confidence": raw})
    assert signal.confidence == expected


def test_invalid_category_rejected() -> None:
    with pytest.raises(ValidationError):
        OilSignal.model_validate({**_VALID, "event_category": "not_a_category"})
