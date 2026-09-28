"""FastAPI dependencies: DB session, current-user resolution, role
enforcement, and CSRF double-submit checking (ADR-0001).

FR-AUTH-002: role and authorized-record scope are resolved here, before the
business action executes - route handlers and services still filter every
query by ownership/department at the query level (NFR-SEC-006/007), this
dependency only proves *who* is calling and *what role* they hold.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.core.security import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    decode_access_token,
)
from app.db.session import get_db
from app.models.user import User, UserRole

DbSession = Annotated[Session, Depends(get_db)]

# Injected via FastAPI's dependency system (rather than called directly)
# so tests can override `get_rate_limiter` with an in-memory fake instead
# of requiring a live Redis server (ADR-0006).
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

_UNAUTHENTICATED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        raise _UNAUTHENTICATED
    try:
        payload = decode_access_token(token)
    except Exception:  # noqa: BLE001 - any decode/verify failure is "not authenticated"
        raise _UNAUTHENTICATED from None

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except (ValueError, AttributeError, TypeError):
        raise _UNAUTHENTICATED from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED
    if payload.get("token_version") != user.token_version:
        # Logout/deactivation/reset incremented token_version - this JWT is revoked (NFR-SEC-004).
        raise _UNAUTHENTICATED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole):
    def _dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        return user

    return _dependency


def csrf_protect(request: Request) -> None:
    """Double-submit CSRF check (ADR-0001): required on every state-changing
    request. A missing/mismatched pair is rejected with 403."""
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")
