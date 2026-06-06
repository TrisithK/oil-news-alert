"""Curated RSS ingestion via feedparser.

We fetch the raw feed through the shared HTTP client (for backoff + the host allowlist) and
hand the bytes to feedparser, which keeps parsing unit-testable against fixtures.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import time

import feedparser

from worker.ingest.client import fetch
from worker.ingest.normalize import NormalizedArticle

log = logging.getLogger(__name__)

_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    return _WS.sub(" ", _TAGS.sub(" ", text)).strip() or None


def _entry_datetime(entry: feedparser.FeedParserDict) -> dt.datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return dt.datetime.fromtimestamp(time.mktime(parsed), tz=dt.UTC)


def parse_rss(content: bytes | str) -> list[NormalizedArticle]:
    feed = feedparser.parse(content)
    language = feed.feed.get("language") if hasattr(feed, "feed") else None
    out: list[NormalizedArticle] = []
    for e in feed.entries:
        url = e.get("link")
        title = e.get("title")
        if not url or not title:
            continue
        out.append(
            NormalizedArticle(
                url=url,
                title=title,
                source_kind="rss",
                external_id=e.get("id") or url,
                body=_strip_html(e.get("summary")),
                published_at=_entry_datetime(e),
                language=language,
                raw={
                    "title": title,
                    "link": url,
                    "summary": e.get("summary"),
                    "published": e.get("published"),
                },
            )
        )
    return out


def fetch_rss(url: str) -> list[NormalizedArticle]:
    resp = fetch(url, headers={"Accept": "application/rss+xml, application/xml, text/xml"})
    return parse_rss(resp.content)
