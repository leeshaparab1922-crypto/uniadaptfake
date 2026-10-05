"""SQLAlchemy implementation of `IngestionRepository` (PostgreSQL + pgvector).

Each write commits immediately so the Teacher's ingestion-status view shows
live stage progress and a crash never loses completed stage records.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.content import (
    ContentChunk,
    ContentType,
    ContentVersion,
    ContentVersionStatus,
    IngestionStage,
    IngestionStageRun,
    IngestionStatus,
    LocatorType,
    StageStatus,
)
from app.services.ingestion.chunking import Chunk
from app.services.ingestion.errors import IngestionInProgress, IngestionNotNeeded
from app.services.ingestion_retry import is_stale_running
from app.services.ingestion_service import IngestionContext


class SqlIngestionRepository:
    def __init__(
        self,
        db: Session,
        *,
        stale_after_seconds: int,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._db = db
        self._stale_after_seconds = stale_after_seconds
        self._now = now

    def _version(self, version_id: str) -> ContentVersion:
        version = self._db.get(ContentVersion, uuid.UUID(version_id))
        if version is None:
            raise LookupError("ContentVersion not found")
        return version

    def begin_attempt(self, version_id: str) -> int:
        # Row lock: two deliveries of the same version (a retry during Celery's own retry
        # backoff, a double-clicked Retry) cannot both start, and attempt numbers stay unique
        # (finding m1). A RUNNING version is only taken over once it is stale (finding M2).
        version = self._db.execute(
            select(ContentVersion)
            .where(ContentVersion.id == uuid.UUID(version_id))
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if version is None:
            raise LookupError("ContentVersion not found")
        if (
            version.status != ContentVersionStatus.DRAFT
            or version.ingestion_status == IngestionStatus.SUCCEEDED
        ):
            self._db.rollback()
            raise IngestionNotNeeded("This version was already ingested; nothing to do.")
        now = self._now()
        if version.ingestion_status == IngestionStatus.RUNNING and not is_stale_running(
            ingestion_status=version.ingestion_status.value,
            heartbeat_at=version.ingestion_heartbeat_at,
            now=now,
            stale_after_seconds=self._stale_after_seconds,
        ):
            self._db.rollback()
            raise IngestionInProgress("Ingestion of this version is already running in another worker.")
        last = self._db.scalar(
            select(func.max(IngestionStageRun.attempt)).where(
                IngestionStageRun.content_version_id == version.id
            )
        )
        version.ingestion_status = IngestionStatus.RUNNING
        version.ingestion_heartbeat_at = now
        version.failed_stage = None
        version.failure_message = None
        self._db.commit()
        return (last or 0) + 1

    def _touch(self, version_id: uuid.UUID) -> None:
        self._db.execute(
            update(ContentVersion)
            .where(ContentVersion.id == version_id)
            .values(ingestion_heartbeat_at=self._now())
        )

    def stage_succeeded_before(self, version_id: str, stage: str) -> bool:
        return (
            self._db.scalar(
                select(IngestionStageRun.id).where(
                    IngestionStageRun.content_version_id == uuid.UUID(version_id),
                    IngestionStageRun.stage == IngestionStage(stage),
                    IngestionStageRun.status == StageStatus.SUCCEEDED,
                )
            )
            is not None
        )

    def record_stage(
        self,
        version_id: str,
        stage: str,
        attempt: int,
        status: str,
        started_at: datetime,
        finished_at: datetime | None,
        detail: dict | None,
        error: str | None,
    ) -> None:
        vid = uuid.UUID(version_id)
        row = self._db.scalar(
            select(IngestionStageRun).where(
                IngestionStageRun.content_version_id == vid,
                IngestionStageRun.stage == IngestionStage(stage),
                IngestionStageRun.attempt == attempt,
            )
        )
        if row is None:
            row = IngestionStageRun(content_version_id=vid, stage=IngestionStage(stage), attempt=attempt)
            self._db.add(row)
        row.status = StageStatus(status)
        row.started_at = started_at
        row.finished_at = finished_at
        row.detail = detail
        row.error = (error or None) and error[:1000]
        self._touch(vid)
        self._db.commit()

    def chunk_count(self, version_id: str) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(ContentChunk)
                .where(ContentChunk.content_version_id == uuid.UUID(version_id))
            )
            or 0
        )

    def delete_chunks(self, version_id: str) -> None:
        version = self._version(version_id)
        if version.status != ContentVersionStatus.DRAFT:
            raise PermissionError("Chunks of an approved (ACTIVE/SUPERSEDED) version are immutable.")
        self._db.execute(delete(ContentChunk).where(ContentChunk.content_version_id == version.id))
        self._db.commit()

    def insert_chunks(self, ctx: IngestionContext, chunks: Sequence[Chunk]) -> None:
        for index, chunk in enumerate(chunks):
            self._db.add(
                ContentChunk(
                    subject_id=uuid.UUID(ctx.subject_id),
                    content_version_id=uuid.UUID(ctx.version_id),
                    unit_no=chunk.unit_no,
                    source_file=ctx.source_file,
                    locator_type=LocatorType(chunk.locator_type),
                    locator=chunk.locator,
                    page_no=chunk.page_no,
                    chunk_type=ContentType(ctx.chunk_type),
                    chunk_index=index,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    text_sha256=hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                    embedding=None,
                    embedding_config_id=uuid.UUID(ctx.embedding_config_id),
                )
            )
        self._db.commit()

    def chunks_missing_embeddings(self, version_id: str, limit: int) -> list[tuple[str, str]]:
        rows = self._db.execute(
            select(ContentChunk.id, ContentChunk.text)
            .where(
                ContentChunk.content_version_id == uuid.UUID(version_id),
                ContentChunk.embedding.is_(None),
            )
            .order_by(ContentChunk.chunk_index)
            .limit(limit)
        ).all()
        return [(str(r[0]), r[1]) for r in rows]

    def set_embeddings(self, version_id: str, embeddings: dict[str, list[float]]) -> None:
        version = self._version(version_id)
        if version.status != ContentVersionStatus.DRAFT:
            raise PermissionError("Chunks of an approved (ACTIVE/SUPERSEDED) version are immutable.")
        for chunk_id, vector in embeddings.items():
            self._db.execute(
                update(ContentChunk)
                .where(
                    ContentChunk.id == uuid.UUID(chunk_id),
                    ContentChunk.content_version_id == uuid.UUID(version_id),
                )
                .values(embedding=vector)
            )
        self._touch(version.id)
        self._db.commit()

    def count_missing_embeddings(self, version_id: str) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(ContentChunk)
                .where(
                    ContentChunk.content_version_id == uuid.UUID(version_id),
                    ContentChunk.embedding.is_(None),
                )
            )
            or 0
        )

    def finalize_success(self, version_id: str, embedding_config_id: str) -> None:
        version = self._version(version_id)
        version.ingestion_status = IngestionStatus.SUCCEEDED
        version.embedding_config_id = uuid.UUID(embedding_config_id)
        version.failed_stage = None
        version.failure_message = None
        self._db.commit()

    def finalize_failure(self, version_id: str, stage: str, message: str) -> None:
        version = self._version(version_id)
        version.ingestion_status = IngestionStatus.FAILED
        version.failed_stage = stage
        version.failure_message = message[:1000]
        self._db.commit()

    def fail_running_attempt(self, version_id: str, message: str) -> None:
        """Mark the in-flight attempt FAILED (e.g. the job hit its time limit, finding M5),
        so the version is retryable at once instead of waiting to become stale."""
        vid = uuid.UUID(version_id)
        self._db.rollback()
        running = list(
            self._db.scalars(
                select(IngestionStageRun)
                .where(
                    IngestionStageRun.content_version_id == vid,
                    IngestionStageRun.status == StageStatus.RUNNING,
                )
                .order_by(IngestionStageRun.started_at)
            )
        )
        now = self._now()
        for row in running:
            row.status = StageStatus.FAILED
            row.finished_at = now
            row.error = message[:1000]
        version = self._version(version_id)
        if version.ingestion_status in (IngestionStatus.RUNNING, IngestionStatus.FAILED):
            version.ingestion_status = IngestionStatus.FAILED
            if running:
                version.failed_stage = running[-1].stage.value
            version.failure_message = message[:1000]
        self._db.commit()
