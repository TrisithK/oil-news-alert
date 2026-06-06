"""Article normalization and content hashing.

The dedup key is a SHA-256 of the normalized ``title`` + ``url`` (§5). Normalizing first
means trivial variations — casing, whitespace, http/https, a trailing slash, a URL fragment —
collapse to the same hash, so reworded-but-identical links don't slip through as new items.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

_WS = re.compile(r"\s+")
_SCHEME = re.compile(r"^https?://", re.IGNORECASE)
_FRAGMENT = re.compile(r"#.*$")


def normalize_title(title: str | None) -> str:
    return _WS.sub(" ", (title or "").strip()).lower()


def normalize_url(url: str | None) -> str:
    u = (url or "").strip()
    u = _SCHEME.sub("", u)
    u = _FRAGMENT.sub("", u)
    u = u.rstrip("/")
    return u.lower()


def compute_content_hash(title: str | None, url: str | None) -> str:
    basis = f"{normalize_title(title)}|{normalize_url(url)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


@dataclass
class NormalizedArticle:
    """Source-agnostic article shape produced by every fetcher."""

    url: str
    title: str
    source_kind: str  # gdelt | rss | api
    external_id: str | None = None
    body: str | None = None
    published_at: dt.datetime | None = None
    language: str | None = None
    source_country: str | None = None
    tone: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return compute_content_hash(self.title, self.url)
