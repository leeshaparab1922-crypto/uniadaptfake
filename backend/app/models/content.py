"""Shared Subject content: ContentAsset/ContentVersion, ingestion stage runs,
ContentChunk, ApprovedResourceLink. FR-CON-001..004, SRS Section 31.2.

All tables here are PostgreSQL-only (`info={"pg_only": True}`): they use
pgvector and partial unique indexes, so the Phase 1 SQLite fixtures skip them
and every Phase 2 DB test runs against the compose Postgres service.

ADR-0009: enums are VARCHAR + named CHECK. ADR-0018: `storage_key` follows
the write-once key layout.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.embedding_config import EMBEDDING_DIMENSION

_PG = {"info": {"pg_only": True}}


def _enum(py_enum: type[enum.Enum], name: str, length: int) -> SAEnum:
    return SAEnum(py_enum, name=name, native_enum=False, create_constraint=True, length=length)


class ContentType(str, enum.Enum):
    """Upload content type == chunk_type (plan assumption A-3)."""

    SYLLABUS = "SYLLABUS"
    NOTES = "NOTES"
    PPT = "PPT"
    PYQ = "PYQ"
    LAB = "LAB"


class ContentVersionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class IngestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class IngestionStage(str, enum.Enum):
    VALIDATE = "VALIDATE"
    EXTRACT = "EXTRACT"
    OCR = "OCR"
    CLEAN = "CLEAN"
    CHUNK = "CHUNK"
    EMBED = "EMBED"
    STORE = "STORE"


class StageStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class LocatorType(str, enum.Enum):
    PAGE = "PAGE"
    SLIDE = "SLIDE"
    SECTION = "SECTION"
    LINES = "LINES"


class LinkStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"


class ContentAsset(Base, TimestampMixin):
    __tablename__ = "content_assets"
    __table_args__ = (
        Index(
            "uq_one_syllabus_asset_per_subject",
            "subject_id",
            unique=True,
            postgresql_where=text("content_type = 'SYLLABUS'"),
        ),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    content_type: Mapped[ContentType] = mapped_column(_enum(ContentType, "content_type", 16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)


class ContentVersion(Base, TimestampMixin):
    __tablename__ = "content_versions"
    __table_args__ = (
        UniqueConstraint("content_asset_id", "version_no", name="uq_content_version_no_per_asset"),
        UniqueConstraint("storage_key", name="uq_content_version_storage_key"),
        Index(
            "uq_one_active_version_per_asset",
            "content_asset_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint("size_bytes >= 1 AND size_bytes <= 26214400", name="ck_content_versions_size_bytes"),
        CheckConstraint("ext IN ('pdf', 'pptx', 'docx', 'txt')", name="ck_content_versions_ext"),
        CheckConstraint(
            "status <> 'ACTIVE' OR ingestion_status = 'SUCCEEDED'",
            name="ck_content_versions_active_requires_ingested",
        ),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_assets.id", ondelete="RESTRICT"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ContentVersionStatus] = mapped_column(
        _enum(ContentVersionStatus, "content_version_status", 16), nullable=False
    )
    ingestion_status: Mapped[IngestionStatus] = mapped_column(
        _enum(IngestionStatus, "ingestion_status", 16), nullable=False
    )
    failed_stage: Mapped[str | None] = mapped_column(String(16), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Last ingestion activity; drives the stale-RUNNING retry rule (finding M2).
    ingestion_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    ext: Mapped[str] = mapped_column(String(8), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("embedding_configs.id", ondelete="RESTRICT"), nullable=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    activated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_versions.id", ondelete="RESTRICT"), nullable=True
    )


class IngestionStageRun(Base):
    __tablename__ = "ingestion_stage_runs"
    __table_args__ = (
        UniqueConstraint("content_version_id", "stage", "attempt", name="uq_stage_run_per_attempt"),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_versions.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[IngestionStage] = mapped_column(
        _enum(IngestionStage, "ingestion_stage", 16), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[StageStatus] = mapped_column(_enum(StageStatus, "stage_status", 16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ContentChunk(Base):
    """Traceable retrieval unit (FR-CON-003). Insert-only once its version is
    approved; `embedding` is NULL only while ingestion is mid-flight and such
    chunks are never returned by retrieval."""

    __tablename__ = "content_chunks"
    __table_args__ = (
        UniqueConstraint("content_version_id", "chunk_index", name="uq_chunk_index_per_version"),
        CheckConstraint("token_count >= 1 AND token_count <= 800", name="ck_content_chunks_token_count"),
        CheckConstraint("length(trim(locator)) > 0", name="ck_content_chunks_locator_nonempty"),
        CheckConstraint("length(trim(text)) > 0", name="ck_content_chunks_text_nonempty"),
        Index(
            "ix_content_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_content_chunks_subject_version", "subject_id", "content_version_id"),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_versions.id", ondelete="RESTRICT"), nullable=False
    )
    unit_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    locator_type: Mapped[LocatorType] = mapped_column(_enum(LocatorType, "locator_type", 16), nullable=False)
    locator: Mapped[str] = mapped_column(String(512), nullable=False)
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_type: Mapped[ContentType] = mapped_column(_enum(ContentType, "chunk_type", 16), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)
    embedding_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("embedding_configs.id", ondelete="RESTRICT"), nullable=False
    )


class ApprovedResourceLink(Base, TimestampMixin):
    """Recommendation-only HTTPS link (BUS-047). Deliberately has no chunk or
    embedding relationship: links are never crawled, embedded, or cited."""

    __tablename__ = "approved_resource_links"
    __table_args__ = (
        CheckConstraint("url LIKE 'https://%'", name="ck_approved_resource_links_https"),
        CheckConstraint(
            "est_minutes IS NULL OR est_minutes > 0", name="ck_approved_resource_links_est_minutes"
        ),
        CheckConstraint(
            "resource_type IN ('ARTICLE', 'VIDEO', 'BOOK', 'TUTORIAL', 'OTHER')",
            name="ck_approved_resource_links_resource_type",
        ),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    topic_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    est_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[LinkStatus] = mapped_column(_enum(LinkStatus, "link_status", 16), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_link_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("approved_resource_links.id", ondelete="RESTRICT"), nullable=True
    )
