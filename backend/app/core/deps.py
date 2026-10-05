"""FastAPI dependencies: DB session, current-user resolution, role
enforcement, and CSRF double-submit checking (ADR-0001).

FR-AUTH-002: role and authorized-record scope are resolved here, before the
business action executes - route handlers and services still filter every
query by ownership/department at the query level (NFR-SEC-006/007), this
dependency only proves *who* is calling and *what role* they hold.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.errors import ServiceUnavailableError
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.core.security import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    decode_access_token,
)
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.curriculum_service import CurriculumQueue
from app.services.ingestion.ports import Embedder, IngestionQueue, ObjectStore

logger = logging.getLogger(__name__)

STORAGE_UNAVAILABLE_MESSAGE = (
    "File storage is not available right now. Ask the administrator to check the server setup."
)

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


def get_object_store() -> ObjectStore:
    """MinIO object store (ADR-0018). Overridable in tests via `dependency_overrides`.

    A missing scoped credential is a server configuration problem: it is logged in full and
    the Teacher gets a generic 503, never the setting names (finding N6, NFR-SEC-011)."""
    from app.integrations.object_store import MinioObjectStore

    try:
        return MinioObjectStore.from_settings()
    except ValueError:
        logger.exception("MinIO object store is not configured")
        raise ServiceUnavailableError(STORAGE_UNAVAILABLE_MESSAGE) from None


def get_ingestion_queue() -> IngestionQueue:
    """Celery-backed queue. Overridable in tests (recorder / eager execution)."""
    from app.workers.ingestion_tasks import CeleryIngestionQueue

    return CeleryIngestionQueue()


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Local bge-m3 embedder (ADR-0015), loaded lazily once per process; the model is only
    read when a Topic actually needs embedding. Overridable in tests."""
    global _embedder
    if _embedder is None:
        from app.integrations.embedding import BgeM3Embedder

        _embedder = BgeM3Embedder()
    return _embedder


def get_curriculum_queue() -> CurriculumQueue:
    """Celery-backed queue for curriculum generation. Overridable in tests."""
    from app.workers.curriculum_tasks import CeleryCurriculumQueue

    return CeleryCurriculumQueue()


ObjectStoreDep = Annotated[ObjectStore, Depends(get_object_store)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
CurriculumQueueDep = Annotated[CurriculumQueue, Depends(get_curriculum_queue)]
IngestionQueueDep = Annotated[IngestionQueue, Depends(get_ingestion_queue)]


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
