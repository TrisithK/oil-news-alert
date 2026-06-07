"""FastAPI application entrypoint.

Phase 0 ships the skeleton (health + root + OpenAPI). Feature routers (feed, alerts,
config, sources, stats, feedback, SSE stream) are added in Phase 4.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup/shutdown hooks (SSE hub, etc.) wire in here in later phases.
    yield


app = FastAPI(
    title="Oil News Alert API",
    version="0.1.0",
    description=(
        "AI system that monitors global news for events likely to move ICE Brent, "
        "scores each item for trading importance and direction, and pushes alerts to "
        "traders. Decision-support with a human in the loop."
    ),
    lifespan=lifespan,
)

# Origins are env-driven (CORS_ORIGINS); defaults to "*" for local dev. Auth is a bearer header,
# not cookies, so credentials are off — which keeps "*" valid.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"service": "oil-news-alert", "docs": "/docs"}
