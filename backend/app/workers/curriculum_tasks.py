"""Celery task for Curriculum Agent generation (FR-CUR-001, BUS-040, ASM-004).

Idempotent: a version that is no longer GENERATING is a no-op. When the provider is unreachable
the task retries with backoff and keeps nothing partial; when retries are exhausted the version
becomes GENERATION_FAILED, and the Subject Owner can still activate the flat Unit-order fallback.
"""

from __future__ import annotations

import logging
import uuid

from celery.exceptions import Retry, SoftTimeLimitExceeded

from app.agents.curriculum_runner import run_generation
from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.embedding import BgeM3Embedder
from app.integrations.llm.anthropic_adapter import build_provider
from app.services.curriculum_service import mark_generation_failed
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

OUTAGE_MESSAGE = (
    "Curriculum generation could not reach the AI provider and ran out of retries. "
    "Try again later, or ask the Subject Owner to activate the flat Unit-order fallback."
)

TIME_LIMIT_MESSAGE = (
    "Curriculum generation took longer than the time limit and was stopped. Try again, or ask the "
    "Subject Owner to activate the flat Unit-order fallback."
)
UNEXPECTED_MESSAGE = (
    "Curriculum generation failed because of a server error. Try again, or ask the Subject Owner to "
    "activate the flat Unit-order fallback."
)

_embedder: BgeM3Embedder | None = None


def _get_embedder() -> BgeM3Embedder:
    global _embedder
    if _embedder is None:
        _embedder = BgeM3Embedder()
    return _embedder


def _caused_by_time_limit(exc: BaseException) -> bool:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        if isinstance(current, SoftTimeLimitExceeded):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


def _fail(version_id: uuid.UUID, message: str) -> None:
    """Record the failure in a fresh session (the task's own session may be unusable)."""
    with SessionLocal() as db:
        mark_generation_failed(db, version_id, message)


@celery_app.task(
    bind=True,
    name="curriculum.generate_curriculum",
    max_retries=settings.curriculum_generation_max_attempts,
    acks_late=True,
    # Sized to the LLM call budget, not the ingestion limits (finding D1).
    soft_time_limit=settings.effective_curriculum_soft_time_limit_seconds,
    time_limit=settings.effective_curriculum_time_limit_seconds,
)
def generate_curriculum(self, curriculum_version_id: str) -> dict:
    version_id = uuid.UUID(curriculum_version_id)
    try:
        with SessionLocal() as db:
            outcome = run_generation(
                db, version_id, provider=build_provider(settings.llm_provider), embedder=_get_embedder()
            )
            if outcome.retry:
                if self.request.retries >= self.max_retries:
                    mark_generation_failed(db, version_id, OUTAGE_MESSAGE, agent_run_id=outcome.agent_run_id)
                    return {"status": "GENERATION_FAILED", "reason": "outage_retries_exhausted"}
                raise self.retry(countdown=min(600, 30 * 2**self.request.retries))
    except Retry:
        raise
    except Exception as exc:
        # Never leave the version GENERATING (finding D1): a provider-config or prompt-registry
        # error, a database error, or the worker time limit all end as GENERATION_FAILED.
        if _caused_by_time_limit(exc):
            logger.warning("Curriculum generation %s hit the time limit", curriculum_version_id)
            _fail(version_id, TIME_LIMIT_MESSAGE)
            return {"status": "GENERATION_FAILED", "reason": "time_limit"}
        logger.exception("Curriculum generation %s failed unexpectedly", curriculum_version_id)
        _fail(version_id, UNEXPECTED_MESSAGE)
        return {"status": "GENERATION_FAILED", "reason": "unexpected_error"}
    logger.info("Curriculum generation %s finished: %s", curriculum_version_id, outcome.status)
    return {"status": outcome.status}


class CeleryCurriculumQueue:
    """`CurriculumQueue` port backed by Celery (default dependency in production)."""

    def enqueue(self, curriculum_version_id: str) -> None:
        generate_curriculum.delay(curriculum_version_id)
