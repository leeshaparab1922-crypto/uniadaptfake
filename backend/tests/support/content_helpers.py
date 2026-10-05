"""DB helpers for Phase 2 PostgreSQL tests (rows created directly, no MinIO needed)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.integrations.object_store import build_storage_key
from app.models.content import (
    ContentAsset,
    ContentChunk,
    ContentType,
    ContentVersion,
    ContentVersionStatus,
    IngestionStatus,
    LocatorType,
)
from app.models.embedding_config import EmbeddingConfig
from app.models.user import User
from tests.support.fakes import FakeEmbedder


def make_embedding_config(db: Session, *, revision: str | None = None) -> EmbeddingConfig:
    cfg = EmbeddingConfig(
        model_id="BAAI/bge-m3",
        model_revision=revision or uuid.uuid4().hex,
        tokenizer_revision="x",
        dimension=1024,
        normalized=True,
        max_chunk_tokens=800,
        chunk_overlap_tokens=120,
    )
    db.add(cfg)
    db.flush()
    return cfg


def make_asset(
    db: Session, *, subject_id, actor: User, content_type=ContentType.NOTES, title="Notes"
) -> ContentAsset:
    asset = ContentAsset(subject_id=subject_id, content_type=content_type, title=title, created_by=actor.id)
    db.add(asset)
    db.flush()
    return asset


_NOW_IF_RUNNING = object()


def make_version(
    db: Session,
    *,
    asset: ContentAsset,
    actor: User,
    version_no: int,
    status=ContentVersionStatus.DRAFT,
    ingestion=IngestionStatus.SUCCEEDED,
    unit_id=None,
    ext: str = "txt",
    heartbeat_at=_NOW_IF_RUNNING,
) -> ContentVersion:
    """A RUNNING version gets a fresh heartbeat unless `heartbeat_at` is given (finding M2)."""
    if heartbeat_at is _NOW_IF_RUNNING:
        heartbeat_at = datetime.now(UTC) if ingestion == IngestionStatus.RUNNING else None
    vid = uuid.uuid4()
    data = f"v{version_no}-{vid}".encode()
    version = ContentVersion(
        id=vid,
        content_asset_id=asset.id,
        version_no=version_no,
        status=status,
        ingestion_status=ingestion,
        ingestion_heartbeat_at=heartbeat_at,
        unit_id=unit_id,
        storage_key=build_storage_key(asset.subject_id, asset.id, vid, ext),
        original_filename=f"file-v{version_no}.{ext}",
        ext=ext,
        mime_type="text/plain",
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=actor.id,
    )
    db.add(version)
    db.flush()
    return version


def make_chunk(
    db: Session,
    *,
    version: ContentVersion,
    subject_id,
    config: EmbeddingConfig,
    index: int,
    text: str,
    unit_no: int | None = 1,
    embedded: bool = True,
    locator: str = "page:1",
    chunk_type=ContentType.NOTES,
) -> ContentChunk:
    chunk = ContentChunk(
        subject_id=subject_id,
        content_version_id=version.id,
        unit_no=unit_no,
        source_file=version.original_filename,
        locator_type=LocatorType.PAGE,
        locator=locator,
        page_no=1,
        chunk_type=chunk_type,
        chunk_index=index,
        text=text,
        token_count=max(1, len(text.split())),
        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        embedding=FakeEmbedder.vector_for(text) if embedded else None,
        embedding_config_id=config.id,
    )
    db.add(chunk)
    db.flush()
    return chunk
