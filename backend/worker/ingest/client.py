"""Shared outbound HTTP client: rate-limit-friendly retries + a host allowlist.

Guardrails (§5/§18): exponential backoff on every external call, and an allowlist so the
worker only fetches from domains we've explicitly seeded. The allowlist is enforced only
once populated, so unit tests (which parse fixtures, never hitting the network) are unaffected.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger(__name__)

_USER_AGENT = "oil-news-alert/0.1 (portfolio MVP; +https://example.com)"

ALLOWED_HOSTS: set[str] = set()


def allow_host(host: str | None) -> None:
    if host:
        ALLOWED_HOSTS.add(host.lower())


def allow_url(url: str | None) -> None:
    if url:
        allow_host(urlparse(url).hostname)


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def _is_retryable(exc: BaseException) -> bool:
    """Retry transient failures only — network errors, 429, and 5xx — never permanent 4xx."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, max=30),
    retry=retry_if_exception(_is_retryable),
)
def fetch(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 20.0,
) -> httpx.Response:
    """GET ``url`` with retries/backoff. Raises if the host is not allowlisted."""
    if ALLOWED_HOSTS and not _host_allowed(url):
        raise PermissionError(f"Outbound host not allowlisted: {url}")
    merged = {"User-Agent": _USER_AGENT, **(headers or {})}
    resp = httpx.get(url, params=params, headers=merged, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return resp
