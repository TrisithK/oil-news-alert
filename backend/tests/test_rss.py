from __future__ import annotations

from pathlib import Path

from worker.ingest.rss import parse_rss


def test_parse_rss(fixtures_dir: Path) -> None:
    items = parse_rss((fixtures_dir / "rss_sample.xml").read_bytes())
    assert len(items) == 2

    first = items[0]
    assert first.source_kind == "rss"
    assert "Brent" in first.title
    assert first.language == "en-us"
    assert first.published_at is not None
    # HTML is stripped out of the summary body.
    assert first.body is not None
    assert "Brent rose" in first.body
    assert "<p>" not in first.body
