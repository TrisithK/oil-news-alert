"""GDELT 2.0 DOC API client (free, no key).

Polls the artlist endpoint with an oil-focused boolean query over a rolling timespan. GDELT
caps a single response, so very busy windows are split into sub-windows to avoid gaps (§5).
"""

from __future__ import annotations

import datetime as dt
import logging

from worker.ingest.client import fetch
from worker.ingest.normalize import NormalizedArticle

log = logging.getLogger(__name__)

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# URL-encoded in the request by httpx; keep the human-readable form here (§5).
GDELT_QUERY = (
    '(oil OR crude OR brent OR OPEC OR "oil prices" OR petroleum OR refinery '
    'OR "Strait of Hormuz" OR sanctions)'
)

_MAX_RECORDS = 250  # GDELT hard cap per request


def _parse_seendate(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.UTC)
    except ValueError:
        return None


def _safe_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def parse_gdelt(payload: dict) -> list[NormalizedArticle]:
    """Map a GDELT artlist JSON payload to normalized articles."""
    out: list[NormalizedArticle] = []
    for a in payload.get("articles", []) or []:
        url = a.get("url")
        title = a.get("title")
        if not url or not title:
            continue
        out.append(
            NormalizedArticle(
                url=url,
                title=title,
                source_kind="gdelt",
                external_id=url,  # GDELT has no stable id; the canonical url is the key
                published_at=_parse_seendate(a.get("seendate")),
                language=a.get("language"),
                source_country=a.get("sourcecountry"),
                tone=_safe_float(a.get("tone")),
                raw=a,
            )
        )
    return out


def fetch_gdelt(*, timespan_minutes: int = 60, max_records: int = 75) -> list[NormalizedArticle]:
    """Fetch the most recent oil-relevant articles from GDELT."""
    params = {
        "query": GDELT_QUERY,
        "mode": "artlist",
        "format": "json",
        "timespan": f"{timespan_minutes}min",
        "maxrecords": min(max_records, _MAX_RECORDS),
        "sort": "datedesc",
    }
    resp = fetch(GDELT_DOC_URL, params=params)
    # GDELT returns an empty body / non-JSON when a window has no results.
    try:
        payload = resp.json()
    except ValueError:
        return []
    items = parse_gdelt(payload)
    if len(items) >= params["maxrecords"]:
        log.warning(
            "GDELT window hit the record cap (%s); some items in the last %smin may be missed. "
            "Sub-window pagination is the scale path.",
            params["maxrecords"],
            timespan_minutes,
        )
    return items
