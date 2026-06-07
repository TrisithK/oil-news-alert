"""Assembles all API routers under one bearer-token-protected router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api import (
    routes_alerts,
    routes_config,
    routes_feed,
    routes_feedback,
    routes_ingest,
    routes_sources,
    routes_stats,
    routes_stream,
)
from app.core.auth import require_token

api_router = APIRouter(dependencies=[Depends(require_token)])

for _module in (
    routes_feed,
    routes_alerts,
    routes_config,
    routes_sources,
    routes_stats,
    routes_feedback,
    routes_stream,
    routes_ingest,
):
    api_router.include_router(_module.router)
