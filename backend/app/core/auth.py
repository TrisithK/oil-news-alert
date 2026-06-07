"""Auth-lite: a single shared bearer token (spec §9). SSO/RBAC is the production step.

Accepts the token from the ``Authorization: Bearer`` header (REST) or a ``token`` query param
(so a browser EventSource can authenticate the SSE stream).
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Query, status

from app.core.config import settings


def require_token(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> None:
    provided: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    elif token:
        provided = token
    if provided != settings.api_bearer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
        )
