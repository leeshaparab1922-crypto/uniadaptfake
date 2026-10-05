"""Curriculum graph: CurriculumVersion, Topic, TopicVersion, TopicPrereq, mappings, validation
flags, and the versioned duplicate-similarity threshold. FR-CUR-001..004, SRS 31.2/31.3.

PostgreSQL-only (pgvector + partial unique indexes). ADR-0009: enums are VARCHAR + named CHECK.

Plan assumption A-4: a DRAFT CurriculumVersion is a mutable working copy with a `revision`
counter; it is immutable once ACTIVE (service guard). Exam weightage is never stored on a
Topic: it is derived from the Topic's Unit (SRS Section 18, "inherit").
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.embedding_config import EMBEDDING_DIMENSION

_PG = {"info": {"pg_only": True}}


def _enum(py_enum: type[enum.Enum], name: str, length: int) -> SAEnum:
    return SAEnum(py_enum, name=name, native_enum=False, create_constraint=True, length=length)


class ThresholdStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class CurriculumStatus(str, enum.Enum):
    GENERATING = "GENERATING"
    GENERATION_FAILED = "GENERATION_FAILED"
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETURNED = "RETURNED"


class CurriculumOrigin(str, enum.Enum):
    AGENT = "AGENT"
    FLAT_FALLBACK = "FLAT_FALLBACK"


class ValidationStatus(str, enum.Enum):
    NOT_RUN = "NOT_RUN"
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"


class BloomLevel(str, enum.Enum):
    REMEMBER = "REMEMBER"
    UNDERSTAND = "UNDERSTAND"
    APPLY = "APPLY"
    ANALYZE = "ANALYZE"
    EVALUATE = "EVALUATE"
    CREATE = "CREATE"


class TopicClassification(str, enum.Enum):
    CORE = "CORE"
    OPTIONAL = "OPTIONAL"
    SELF_STUDY = "SELF_STUDY"


class EdgeSource(str, enum.Enum):
    AGENT = "AGENT"
    TEACHER = "TEACHER"


class MappingKind(str, enum.Enum):
    RENAME = "RENAME"
    MERGE = "MERGE"
    SPLIT = "SPLIT"


class FlagKind(str, enum.Enum):
    CYCLE_EDGE_DROPPED = "CYCLE_EDGE_DROPPED"
    CYCLE_REMAINING = "CYCLE_REMAINING"
    ORPHAN = "ORPHAN"
    DUPLICATE_TOPIC = "DUPLICATE_TOPIC"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"


class SimilarityThreshold(Base, TimestampMixin):
    """Versioned duplicate-Topic threshold tied to one embedding configuration (BUS-050)."""

    __tablename__ = "similarity_thresholds"
    __table_args__ = (
        CheckConstraint("value >= 0 AND value <= 1", name="ck_similarity_thresholds_value"),
        CheckConstraint(
            "status NOT IN ('VALIDATED', 'ACTIVE') OR validated_at IS NOT NULL",
            name="ck_similarity_thresholds_validated",
        ),
        Index(
            "uq_one_active_threshold_per_name_config",
            "name",
            "embedding_config_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    embedding_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("embedding_configs.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    status: Mapped[ThresholdStatus] = mapped_column(
        _enum(ThresholdStatus, "threshold_status", 16), nullable=False
    )
    validation_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CurriculumVersion(Base, TimestampMixin):
    __tablename__ = "curriculum_versions"
    __table_args__ = (
        UniqueConstraint("subject_id", "version_no", name="uq_curriculum_version_no_per_subject"),
        Index(
            "uq_one_active_curriculum_per_subject",
            "subject_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint("revision >= 1", name="ck_curriculum_versions_revision"),
        CheckConstraint(
            "status <> 'ACTIVE' OR (validation_status = 'PASSED' AND validated_revision = revision)",
            name="ck_curriculum_versions_active_validated",
        ),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CurriculumStatus] = mapped_column(
        _enum(CurriculumStatus, "curriculum_status", 24), nullable=False
    )
    origin: Mapped[CurriculumOrigin] = mapped_column(
        _enum(CurriculumOrigin, "curriculum_origin", 16), nullable=False
    )
    source_content_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_versions.id", ondelete="RESTRICT"), nullable=True
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="RESTRICT"), nullable=True
    )
    embedding_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("embedding_configs.id", ondelete="RESTRICT"), nullable=True
    )
    similarity_threshold_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("similarity_thresholds.id", ondelete="RESTRICT"), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    validated_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_status: Mapped[ValidationStatus] = mapped_column(
        _enum(ValidationStatus, "validation_status", 16), nullable=False, default=ValidationStatus.NOT_RUN
    )
    failure_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    supersedes_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT"), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Topic(Base):
    """Stable Topic identity; all per-version content lives on TopicVersion."""

    __tablename__ = "topics"
    __table_args__ = (_PG,)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TopicVersion(Base):
    __tablename__ = "topic_versions"
    __table_args__ = (
        UniqueConstraint("curriculum_version_id", "topic_id", name="uq_topic_per_curriculum_version"),
        CheckConstraint("est_hours > 0", name="ck_topic_versions_est_hours"),
        Index("ix_topic_versions_cv", "curriculum_version_id"),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT"), nullable=False
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    outcomes: Mapped[list] = mapped_column(JSON, nullable=False)
    bloom_level: Mapped[BloomLevel] = mapped_column(_enum(BloomLevel, "bloom_level", 16), nullable=False)
    est_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    classification: Mapped[TopicClassification] = mapped_column(
        _enum(TopicClassification, "topic_classification", 16), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)
    embedding_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("embedding_configs.id", ondelete="RESTRICT"), nullable=True
    )
    embedding_text_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)


class TopicPrereq(Base):
    __tablename__ = "topic_prereqs"
    __table_args__ = (
        UniqueConstraint("curriculum_version_id", "topic_id", "prereq_topic_id", name="uq_topic_prereq_edge"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_topic_prereqs_confidence"),
        CheckConstraint("topic_id <> prereq_topic_id", name="ck_topic_prereqs_not_self"),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False)
    prereq_topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    # Cross-subject edge (A-6): pins the exact ACTIVE version of the earlier-semester Subject.
    prereq_curriculum_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT"), nullable=True
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    approved_by_teacher: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[EdgeSource] = mapped_column(_enum(EdgeSource, "edge_source", 16), nullable=False)
    dropped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    drop_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class TopicMapping(Base):
    """Rename/merge/split lineage retained for downstream evidence (SRS Section 18)."""

    __tablename__ = "topic_mappings"
    __table_args__ = (_PG,)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[MappingKind] = mapped_column(_enum(MappingKind, "mapping_kind", 16), nullable=False)
    from_topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    to_topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GraphValidationFlag(Base):
    __tablename__ = "graph_validation_flags"
    __table_args__ = (Index("ix_graph_flags_cv", "curriculum_version_id"), _PG)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[FlagKind] = mapped_column(_enum(FlagKind, "flag_kind", 24), nullable=False)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=True
    )
    other_topic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=True
    )
    edge_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topic_prereqs.id", ondelete="SET NULL"), nullable=True
    )
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TopicSourceChunk(Base):
    """Immutable reference from a Topic (version) to the syllabus chunk it came from (FR-CON-003)."""

    __tablename__ = "topic_source_chunks"
    __table_args__ = (PrimaryKeyConstraint("topic_version_id", "content_chunk_id"), _PG)

    topic_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topic_versions.id", ondelete="CASCADE"), nullable=False
    )
    content_chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_chunks.id", ondelete="RESTRICT"), nullable=False
    )
