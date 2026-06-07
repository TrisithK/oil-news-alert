from __future__ import annotations

import datetime as dt

from app.db.models import Analysis, Config
from worker.alerting.match import config_matches, in_quiet_hours


def _analysis(**overrides: object) -> Analysis:
    base: dict = {
        "importance_score": 90.0,
        "event_category": "geopolitics_conflict",
        "instruments_affected": ["BRENT"],
        "headline_summary": "Israel strikes Iran",
        "rationale": "Risk premium rises",
        "key_entities": ["Iran"],
    }
    base.update(overrides)
    return Analysis(**base)


def _config(**overrides: object) -> Config:
    base: dict = {"min_importance": 70.0}
    base.update(overrides)
    return Config(**base)


def test_threshold() -> None:
    assert config_matches(_config(min_importance=70), _analysis(importance_score=90))
    assert not config_matches(_config(min_importance=95), _analysis(importance_score=90))


def test_instrument_overlap() -> None:
    assert config_matches(
        _config(instruments=["BRENT"]), _analysis(instruments_affected=["BRENT", "WTI"])
    )
    assert not config_matches(
        _config(instruments=["TTF_GAS"]), _analysis(instruments_affected=["BRENT"])
    )


def test_category_filter() -> None:
    assert config_matches(_config(categories=["geopolitics_conflict"]), _analysis())
    assert not config_matches(_config(categories=["inventory_data"]), _analysis())


def test_keyword_filter() -> None:
    assert config_matches(
        _config(keywords=["hormuz"]), _analysis(headline_summary="Strait of Hormuz blocked")
    )
    assert not config_matches(_config(keywords=["opec"]), _analysis())


def test_quiet_hours_overnight_window() -> None:
    cfg = _config(quiet_hours={"start": "22:00", "end": "07:00", "tz": "UTC"})
    night = dt.datetime(2026, 1, 1, 23, 30, tzinfo=dt.UTC)
    day = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.UTC)
    assert in_quiet_hours(cfg, night) is True
    assert in_quiet_hours(cfg, day) is False


def test_quiet_hours_absent() -> None:
    assert in_quiet_hours(_config(), dt.datetime(2026, 1, 1, 3, 0, tzinfo=dt.UTC)) is False
