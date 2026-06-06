from __future__ import annotations

from app.core.taxonomy import Direction, EventCategory, Instrument
from worker.analyze.llm import HeuristicLLMClient, classify_heuristic


def test_hormuz_is_bullish_shipping() -> None:
    signal = classify_heuristic("Tankers reroute near the Strait of Hormuz", None)
    assert signal.event_category is EventCategory.SHIPPING_CHOKEPOINT
    assert signal.expected_direction is Direction.BULLISH
    assert Instrument.BRENT in signal.instruments_affected


def test_opec_cut_vs_hike_direction() -> None:
    cut = classify_heuristic("OPEC+ agrees to deeper voluntary output cuts", None)
    hike = classify_heuristic("OPEC+ to raise output quotas next month", None)
    assert cut.event_category is EventCategory.OPEC_SUPPLY
    assert cut.expected_direction is Direction.BULLISH
    assert hike.expected_direction is Direction.BEARISH


def test_eia_draw_is_scheduled_and_bullish() -> None:
    signal = classify_heuristic("EIA reports a surprise crude oil inventory draw", None)
    assert signal.event_category is EventCategory.INVENTORY
    assert signal.expected_direction is Direction.BULLISH
    assert signal.is_scheduled_data is True


def test_triage_filters_non_oil() -> None:
    llm = HeuristicLLMClient()
    relevant, _ = llm.triage(title="Houthi attack on an oil tanker in the Red Sea", body=None)
    irrelevant, _ = llm.triage(title="Premier League transfer roundup", body=None)
    assert relevant.is_relevant is True
    assert irrelevant.is_relevant is False


def test_extract_returns_valid_signal() -> None:
    llm = HeuristicLLMClient()
    signal, usage, discard = llm.extract(title="EU sanctions Russian crude exports", body=None)
    assert discard is None
    assert signal is not None
    assert signal.event_category is EventCategory.SANCTIONS
    assert usage.prompt_tokens == 0  # offline, no API spend
