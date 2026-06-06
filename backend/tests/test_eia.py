from __future__ import annotations

import json
from pathlib import Path

from worker.ingest.eia import parse_eia


def test_parse_eia_computes_draw(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "eia_weekly.json").read_text())
    items = parse_eia(payload)
    assert len(items) == 1

    art = items[0]
    assert art.source_kind == "api"
    # 418,200 -> 415,000 is a 3,200 kb draw.
    assert "draw" in art.title.lower()
    assert "3,200" in art.title
    assert art.external_id == "eia-WCESTUS1-2025-01-10"
    assert art.published_at is not None


def test_parse_eia_handles_empty() -> None:
    assert parse_eia({"response": {"data": []}}) == []
    assert parse_eia({}) == []
