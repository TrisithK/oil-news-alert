from __future__ import annotations

import pytest

from worker.analyze.prefilter import passes_prefilter


@pytest.mark.parametrize(
    "title",
    [
        "OPEC+ cuts output at weekend meeting",
        "Brent crude rises on supply fears",
        "EIA reports a large inventory draw",
        "Tankers reroute near the Strait of Hormuz",
    ],
)
def test_oil_headlines_pass(title: str) -> None:
    assert passes_prefilter(title) is True


@pytest.mark.parametrize(
    "title",
    [
        "Premier League transfer roundup",
        "Apple unveils a new iPhone",
        "Water is boiling on the stove",  # 'oil' substring must not match
        "Tech stocks hit a record high",
    ],
)
def test_non_oil_headlines_drop(title: str) -> None:
    assert passes_prefilter(title) is False


def test_body_is_considered() -> None:
    assert passes_prefilter("Breaking news", body="A refinery outage hit crude supply") is True
