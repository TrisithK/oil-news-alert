"""In-process pub/sub hub for the live (in-app) channel.

The API's SSE endpoint subscribes; the alerting engine publishes. This gives instant push when
the publisher and subscriber share a process. Across the separate worker/API processes the
durable source of truth is the ``alerts`` table, which the SSE endpoint also polls (spec §3).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

log = logging.getLogger(__name__)


class EventHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def publish(self, event: dict) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover - slow consumer; drop rather than block
                log.warning("SSE subscriber queue full; dropping event")

    async def subscribe(self) -> AsyncIterator[dict]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


event_hub = EventHub()
