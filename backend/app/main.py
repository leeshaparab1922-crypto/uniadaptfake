"""FastAPI app factory, router registration, and exception handlers.

Exception handlers only ever return `str(exc)` from a `DomainError`
subclass - service-layer code is responsible for never putting credential
or token details into those messages (NFR-SEC-011).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    academic_structure,
    admin_accounts,
    auth,
    calendar,
    enrollments,
    students,
    subject_instances,
    subjects,
    teacher,
    teacher_content,
    teacher_curriculum,
)
from app.core.body_limit import BodySizeLimitMiddleware
from app.core.config import settings
from app.core.errors import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PayloadTooLargeError,
    RateLimitedError,
    ServiceUnavailableError,
    ValidationError,
)

# Room for multipart boundaries and the small form fields sent alongside a 25 MB file.
MULTIPART_OVERHEAD_BYTES = 64 * 1024

_ERROR_STATUS_MAP: dict[type[Exception], int] = {
    ValidationError: 400,
    ValueError: 400,
    AuthenticationError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    PayloadTooLargeError: 413,
    ConflictError: 409,
    RateLimitedError: 429,
    ServiceUnavailableError: 503,
}


def _make_handler(status_code: int):
    async def _handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return _handler


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """ADR-0017: sync the prompt registry at startup. A prompt file edited in place after it was
    synced makes startup fail (PromptRegistryError)."""
    if settings.prompt_sync_on_startup:
        from app.db.session import SessionLocal
        from app.prompts.registry import sync_prompts

        with SessionLocal() as db:
            sync_prompts(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="UniAdapt AI API", version="0.1.0", lifespan=_lifespan)

    # Size cap runs before routing, auth, and form parsing. Added before CORS so CORS stays
    # outermost and the browser can still read a 413 from the cap.
    app.add_middleware(
        BodySizeLimitMiddleware,
        max_body_bytes=settings.upload_max_bytes + MULTIPART_OVERHEAD_BYTES,
        limit_mb=settings.upload_max_bytes // (1024 * 1024),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_allowed_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for exc_type, status_code in _ERROR_STATUS_MAP.items():
        app.add_exception_handler(exc_type, _make_handler(status_code))

    app.include_router(auth.router)
    app.include_router(admin_accounts.router)
    app.include_router(academic_structure.router)
    app.include_router(subjects.router)
    app.include_router(subject_instances.router)
    app.include_router(students.router)
    app.include_router(enrollments.router)
    app.include_router(enrollments.admin_router)
    app.include_router(calendar.router)
    app.include_router(teacher.router)
    app.include_router(teacher_content.router)
    app.include_router(teacher_curriculum.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
