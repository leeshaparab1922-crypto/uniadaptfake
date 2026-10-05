"""Glue between the database and the pure `IngestionService`: builds the
ingestion context for a ContentVersion, wires adapters, runs the pipeline.
Used by the Celery task and by tests (with fake ports)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import NotFoundError
from app.models.content import ContentAsset, ContentVersion, ContentVersionStatus, IngestionStatus
from app.models.embedding_config import EMBEDDING_DIMENSION
from app.models.subject import Unit
from app.services.embedding_config_service import get_or_create_active_config
from app.services.ingestion.ports import Embedder, ObjectStore, OcrEngine, Tokenizer
from app.services.ingestion.unit_boundaries import UnitRef
from app.services.ingestion_repository import SqlIngestionRepository
from app.services.ingestion_service import (
    IngestionContext,
    IngestionResult,
    IngestionSettings,
    run_ingestion,
)


def settings_from_config() -> IngestionSettings:
    return IngestionSettings(
        min_page_chars=settings.ingest_min_page_chars,
        render_dpi=settings.ocr_render_dpi,
        ocr_min_mean_confidence=settings.ocr_min_mean_confidence,
        ocr_min_chars=settings.ocr_min_chars,
        blank_ink_ratio=settings.ocr_blank_page_ink_ratio,
        include_pptx_notes=settings.ingest_pptx_notes,
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
        embed_batch_size=settings.embedding_batch_size,
        expected_dimension=EMBEDDING_DIMENSION,
        is_normalized=True,
        max_pdf_pages=settings.ingest_max_pdf_pages,
        archive_max_uncompressed_bytes=settings.ingest_archive_max_uncompressed_bytes,
        archive_max_compression_ratio=settings.ingest_archive_max_compression_ratio,
        archive_max_members=settings.ingest_archive_max_members,
    )


def build_context(db: Session, version: ContentVersion) -> IngestionContext:
    asset = db.get(ContentAsset, version.content_asset_id)
    if asset is None:
        raise NotFoundError("Content asset not found for this version.")
    units = list(
        db.scalars(select(Unit).where(Unit.subject_id == asset.subject_id).order_by(Unit.order_index))
    )
    fixed = None
    if version.unit_id is not None:
        unit = db.get(Unit, version.unit_id)
        fixed = unit.order_index if unit is not None else None
    config = get_or_create_active_config(db)
    return IngestionContext(
        version_id=str(version.id),
        subject_id=str(asset.subject_id),
        chunk_type=asset.content_type.value,
        ext=version.ext,
        source_file=version.original_filename,
        storage_key=version.storage_key,
        sha256=version.sha256,
        size_bytes=version.size_bytes,
        units=[UnitRef(unit_no=u.order_index, name=u.name) for u in units],
        fixed_unit_no=fixed,
        embedding_config_id=str(config.id),
    )


def repository(db: Session) -> SqlIngestionRepository:
    return SqlIngestionRepository(db, stale_after_seconds=settings.effective_ingest_stale_after_seconds)


TIME_LIMIT_MESSAGE = (
    "Processing took longer than the time limit and was stopped. Current content is unchanged. "
    "Retry, or upload a smaller or clearer file."
)


def mark_timed_out(db: Session, version_id: uuid.UUID | str) -> None:
    """Record a job that hit its soft time limit as FAILED at its running stage (finding M5)."""
    repository(db).fail_running_attempt(str(version_id), TIME_LIMIT_MESSAGE)


def ingest_version(
    db: Session,
    version_id: uuid.UUID | str,
    *,
    store: ObjectStore,
    ocr: OcrEngine,
    tokenizer: Tokenizer,
    embedder: Embedder,
    ingestion_settings: IngestionSettings | None = None,
) -> IngestionResult:
    """Idempotent: a SUCCEEDED version is a no-op; ACTIVE/SUPERSEDED versions are never re-ingested."""
    version = db.get(ContentVersion, uuid.UUID(str(version_id)))
    if version is None:
        raise NotFoundError("Content version not found.")
    if version.ingestion_status == IngestionStatus.SUCCEEDED:
        return IngestionResult("SUCCEEDED")
    if version.status != ContentVersionStatus.DRAFT:
        raise NotFoundError("Only DRAFT versions can be ingested.")
    ctx = build_context(db, version)
    return run_ingestion(
        ctx,
        repo=repository(db),
        store=store,
        ocr=ocr,
        tokenizer=tokenizer,
        embedder=embedder,
        settings=ingestion_settings or settings_from_config(),
    )
