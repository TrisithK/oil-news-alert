from __future__ import annotations

from worker.ingest.normalize import (
    NormalizedArticle,
    compute_content_hash,
)


def test_hash_is_stable_and_distinguishes_content() -> None:
    h1 = compute_content_hash("OPEC cuts output", "https://x.com/a")
    h2 = compute_content_hash("OPEC cuts output", "https://x.com/a")
    h3 = compute_content_hash("OPEC raises output", "https://x.com/a")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_normalization_collapses_trivial_variation() -> None:
    # Casing, whitespace, scheme, and a trailing slash must not create a "new" article.
    a = compute_content_hash("  OPEC   Cuts Output ", "HTTPS://X.com/a/")
    b = compute_content_hash("opec cuts output", "http://x.com/a")
    assert a == b


def test_url_fragment_ignored_in_hash() -> None:
    assert compute_content_hash("t", "https://x.com/p#frag") == compute_content_hash(
        "t", "https://x.com/p"
    )


def test_content_hash_property_matches_function() -> None:
    art = NormalizedArticle(url="https://x.com/a", title="Brent up", source_kind="rss")
    assert art.content_hash == compute_content_hash("Brent up", "https://x.com/a")
