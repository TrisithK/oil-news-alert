"""EIA Open Data — weekly U.S. crude oil stocks.

A draw/build is itself a Brent driver, so each new weekly release is normalized into an
"article" that flows through the same analysis pipeline. Surprise-vs-consensus scoring
(the part that really matters for scheduled data) is layered on in Phase 2; here we just
ingest the release. Requires EIA_API_KEY; without one this is skipped.
"""

from __future__ import annotations

import datetime as dt
import logging

from worker.ingest.client import fetch
from worker.ingest.normalize import NormalizedArticle

log = logging.getLogger(__name__)

EIA_WEEKLY_STOCKS_URL = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
# Weekly U.S. Ending Stocks of Crude Oil excluding SPR (thousand barrels).
EIA_CRUDE_SERIES = "WCESTUS1"


def _to_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _period_datetime(period: str | None) -> dt.datetime | None:
    if not period:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return dt.datetime.strptime(period, fmt).replace(tzinfo=dt.UTC)
        except ValueError:
            continue
    return None


def parse_eia(payload: dict) -> list[NormalizedArticle]:
    """Turn a v2 EIA data response (newest period first) into one normalized article."""
    rows = ((payload.get("response") or {}).get("data")) or []
    if not rows:
        return []
    latest = rows[0]
    period = latest.get("period")
    value = _to_float(latest.get("value"))
    if value is None or not period:
        return []
    units = latest.get("units") or "thousand barrels"
    prev = _to_float(rows[1].get("value")) if len(rows) > 1 else None
    change = (value - prev) if prev is not None else None

    if change is None:
        title = f"EIA weekly U.S. crude stocks for {period}: {value:,.0f} {units}"
        body = (
            f"EIA weekly petroleum status: U.S. ending stocks of crude oil (excl. SPR) "
            f"= {value:,.0f} {units} for the week of {period}."
        )
    else:
        direction = "draw" if change < 0 else "build"
        title = (
            f"EIA weekly U.S. crude stocks {direction} of {abs(change):,.0f} {units} for {period}"
        )
        body = (
            f"EIA weekly petroleum status: U.S. ending stocks of crude oil (excl. SPR) "
            f"= {value:,.0f} {units} for the week of {period}, a week-on-week "
            f"{direction} of {abs(change):,.0f} {units}."
        )

    return [
        NormalizedArticle(
            url=f"https://www.eia.gov/petroleum/weekly/#{period}",
            title=title,
            source_kind="api",
            external_id=f"eia-{EIA_CRUDE_SERIES}-{period}",
            body=body,
            published_at=_period_datetime(period),
            source_country="United States",
            raw=latest,
        )
    ]


def fetch_eia_weekly_crude(api_key: str | None, *, n: int = 2) -> list[NormalizedArticle]:
    if not api_key:
        log.info("EIA_API_KEY not set; skipping EIA fundamentals.")
        return []
    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": EIA_CRUDE_SERIES,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": n,
    }
    resp = fetch(EIA_WEEKLY_STOCKS_URL, params=params)
    return parse_eia(resp.json())
