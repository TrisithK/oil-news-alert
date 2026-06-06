from __future__ import annotations

import json
from pathlib import Path

from worker.ingest.gdelt import parse_gdelt


def test_parse_gdelt(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "gdelt_artlist.json").read_text())
    items = parse_gdelt(payload)

    # The entry with no URL is skipped; the other three survive.
    assert len(items) == 3

    hormuz = next(i for i in items if "Hormuz" in i.title)
    assert hormuz.source_kind == "gdelt"
    assert hormuz.tone == -3.5
    assert hormuz.source_country == "United Kingdom"
    assert hormuz.published_at is not None
    assert hormuz.published_at.year == 2025

    # An unparseable seendate degrades to None without dropping the item.
    bad = next(i for i in items if i.url.endswith("/bad-date"))
    assert bad.published_at is None
