"""Celery task for deterministic ingestion (FR-CON-002, BUS-040, NFR-REL-001).

The task is idempotent and resumable: re-delivery of a SUCCEEDED version is a
no-op and a partially ingested version resumes from its persisted chunks.
Permanent failures (empty extraction, unreadable file, OCR failure) are
recorded on the version and are NOT retried; transient infrastructure errors
raise `TransientIngestionError` and are retried with exponential backoff.
"""

from __future__ import annotations

import logging

from celery.exceptions import SoftTimeLimitExceeded

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.embedding import BgeM3Embedder
from app.integrations.object_store import MinioObjectStore
from app.integrations.ocr import TesseractOcrEngine
from app.integrations.tokenizer import BgeM3Tokenizer
from app.services.ingestion.errors import TransientIngestionError
from app.services.ingestion_runtime import ingest_version, mark_timed_out
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_runtime: dict[str, object] = {}


def _adapters() -> dict[str, object]:
    """Heavy adapters (tokenizer/model) are built once per worker process."""
    if not _runtime:
        _runtime.update(
            store=MinioObjectStore.from_settings(),
            ocr=TesseractOcrEngine(),
            tokenizer=BgeM3Tokenizer(),
            embedder=BgeM3Embedder(),
        )
    return _runtime


@celery_app.task(
    bind=True,
    name="ingestion.ingest_content_version",
    autoretry_for=(TransientIngestionError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=settings.ingest_max_attempts,
    acks_late=True,
)
def ingest_content_version(self, content_version_id: str) -> dict:
    adapters = _adapters()
    try:
        with SessionLocal() as db:
            result = ingest_version(
                db,
                content_version_id,
                store=adapters["store"],  # type: ignore[arg-type]
                ocr=adapters["ocr"],  # type: ignore[arg-type]
                tokenizer=adapters["tokenizer"],  # type: ignore[arg-type]
                embedder=adapters["embedder"],  # type: ignore[arg-type]
            )
    except Exception as exc:
        # A time-limit stop may arrive wrapped by a stage, or while a failure was being
        # written (then it is only the context of a database error). Never retry it (N3).
        if _caused_by_time_limit(exc):
            return _timed_out(content_version_id)
        raise
    logger.info("Ingestion of %s finished: %s", content_version_id, result.status)
    return {"status": result.status, "failed_stage": result.failed_stage, "chunks": result.chunk_count}


def _caused_by_time_limit(exc: BaseException) -> bool:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        if isinstance(current, SoftTimeLimitExceeded):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


def _timed_out(content_version_id: str) -> dict:
    logger.warning("Ingestion of %s hit the soft time limit; marking it FAILED.", content_version_id)
    with SessionLocal() as db:
        mark_timed_out(db, content_version_id)
    return {"status": "FAILED", "failed_stage": None, "chunks": 0, "reason": "time_limit"}


class CeleryIngestionQueue:
    """`IngestionQueue` port backed by Celery (default dependency in production)."""

    def enqueue(self, content_version_id: str) -> None:
        ingest_content_version.delay(content_version_id)
