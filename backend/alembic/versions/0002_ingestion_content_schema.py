"""Ingestion & content schema (Phase 2, slice 2A: FR-CON-001..004).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-02

Enums are VARCHAR + named CHECK (ADR-0009). Requires the pgvector extension
(shipped in the `pgvector/pgvector:pg15` image). `embedding_configs` rows are
inserted by `scripts/seed_embedding_config.py`/the ingestion runtime, not here,
because the pinned model revision is an environment decision (ADR-0015).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Kept in step with app.services.resource_link_service.RESOURCE_TYPES (ADR-0009).
RESOURCE_TYPES = ("ARTICLE", "VIDEO", "BOOK", "TUTORIAL", "OTHER")
RESOURCE_TYPES_SQL = ", ".join(f"'{t}'" for t in RESOURCE_TYPES)

CHUNK_GUARD_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION content_chunks_guard() RETURNS trigger AS $$
DECLARE
    version_status varchar;
BEGIN
    SELECT status INTO version_status FROM content_versions WHERE id = OLD.content_version_id;
    IF version_status IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'content_chunks of a % content version are immutable', version_status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF (to_jsonb(NEW) - 'embedding') IS DISTINCT FROM (to_jsonb(OLD) - 'embedding') THEN
            RAISE EXCEPTION 'only the embedding of a content chunk may be updated'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        IF OLD.embedding IS NOT NULL AND NEW.embedding IS DISTINCT FROM OLD.embedding THEN
            RAISE EXCEPTION 'a stored chunk embedding cannot be replaced'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
"""


def _enum(name: str, values: list[str], length: int) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=length)


def _uuid_pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    ]


CONTENT_TYPES = ["SYLLABUS", "NOTES", "PPT", "PYQ", "LAB"]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "embedding_configs",
        _uuid_pk(),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("model_revision", sa.String(64), nullable=False),
        sa.Column("tokenizer_revision", sa.String(64), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("normalized", sa.Boolean(), nullable=False),
        sa.Column("max_chunk_tokens", sa.Integer(), nullable=False),
        sa.Column("chunk_overlap_tokens", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint(
            "model_id", "model_revision", "dimension", "normalized", name="uq_embedding_config_identity"
        ),
        sa.CheckConstraint("dimension = 1024", name="ck_embedding_configs_dimension"),
    )

    op.create_table(
        "content_assets",
        _uuid_pk(),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content_type", _enum("content_type", CONTENT_TYPES, 16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "uq_one_syllabus_asset_per_subject",
        "content_assets",
        ["subject_id"],
        unique=True,
        postgresql_where=sa.text("content_type = 'SYLLABUS'"),
    )

    op.create_table(
        "content_versions",
        _uuid_pk(),
        sa.Column(
            "content_asset_id",
            sa.Uuid(),
            sa.ForeignKey("content_assets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column(
            "status", _enum("content_version_status", ["DRAFT", "ACTIVE", "SUPERSEDED"], 16), nullable=False
        ),
        sa.Column(
            "ingestion_status",
            _enum("ingestion_status", ["PENDING", "RUNNING", "SUCCEEDED", "FAILED"], 16),
            nullable=False,
        ),
        sa.Column("failed_stage", sa.String(16), nullable=True),
        sa.Column("failure_message", sa.String(1000), nullable=True),
        # Last ingestion activity (attempt start / any stage record); a RUNNING version with no
        # activity for longer than the configured timeout may be retried (finding M2).
        sa.Column("ingestion_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unit_id", sa.Uuid(), sa.ForeignKey("units.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("ext", sa.String(8), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "embedding_config_id",
            sa.Uuid(),
            sa.ForeignKey("embedding_configs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("activated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "supersedes_version_id",
            sa.Uuid(),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        *_timestamps(),
        sa.UniqueConstraint("content_asset_id", "version_no", name="uq_content_version_no_per_asset"),
        sa.UniqueConstraint("storage_key", name="uq_content_version_storage_key"),
        sa.CheckConstraint(
            "size_bytes >= 1 AND size_bytes <= 26214400", name="ck_content_versions_size_bytes"
        ),
        sa.CheckConstraint("ext IN ('pdf', 'pptx', 'docx', 'txt')", name="ck_content_versions_ext"),
        sa.CheckConstraint(
            "status <> 'ACTIVE' OR ingestion_status = 'SUCCEEDED'",
            name="ck_content_versions_active_requires_ingested",
        ),
    )
    op.create_index(
        "uq_one_active_version_per_asset",
        "content_versions",
        ["content_asset_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "ingestion_stage_runs",
        _uuid_pk(),
        sa.Column(
            "content_version_id",
            sa.Uuid(),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "stage",
            _enum("ingestion_stage", ["VALIDATE", "EXTRACT", "OCR", "CLEAN", "CHUNK", "EMBED", "STORE"], 16),
            nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column(
            "status", _enum("stage_status", ["RUNNING", "SUCCEEDED", "FAILED", "SKIPPED"], 16), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(1000), nullable=True),
        sa.UniqueConstraint("content_version_id", "stage", "attempt", name="uq_stage_run_per_attempt"),
    )

    op.create_table(
        "content_chunks",
        _uuid_pk(),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "content_version_id",
            sa.Uuid(),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("unit_no", sa.Integer(), nullable=True),
        sa.Column("source_file", sa.String(255), nullable=False),
        sa.Column(
            "locator_type", _enum("locator_type", ["PAGE", "SLIDE", "SECTION", "LINES"], 16), nullable=False
        ),
        sa.Column("locator", sa.String(512), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("chunk_type", _enum("chunk_type", CONTENT_TYPES, 16), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column(
            "embedding_config_id",
            sa.Uuid(),
            sa.ForeignKey("embedding_configs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("content_version_id", "chunk_index", name="uq_chunk_index_per_version"),
        sa.CheckConstraint("token_count >= 1 AND token_count <= 800", name="ck_content_chunks_token_count"),
        sa.CheckConstraint("length(trim(locator)) > 0", name="ck_content_chunks_locator_nonempty"),
        sa.CheckConstraint("length(trim(text)) > 0", name="ck_content_chunks_text_nonempty"),
    )
    op.create_index(
        "ix_content_chunks_subject_version", "content_chunks", ["subject_id", "content_version_id"]
    )
    op.create_index(
        "ix_content_chunks_embedding_hnsw",
        "content_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "approved_resource_links",
        _uuid_pk(),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("topic_label", sa.String(255), nullable=True),
        sa.Column("unit_id", sa.Uuid(), sa.ForeignKey("units.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("est_minutes", sa.Integer(), nullable=True),
        sa.Column("status", _enum("link_status", ["DRAFT", "APPROVED", "SUPERSEDED"], 16), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "supersedes_link_id",
            sa.Uuid(),
            sa.ForeignKey("approved_resource_links.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        *_timestamps(),
        sa.CheckConstraint("url LIKE 'https://%'", name="ck_approved_resource_links_https"),
        sa.CheckConstraint(
            "est_minutes IS NULL OR est_minutes > 0", name="ck_approved_resource_links_est_minutes"
        ),
        sa.CheckConstraint(
            f"resource_type IN ({RESOURCE_TYPES_SQL})", name="ck_approved_resource_links_resource_type"
        ),
    )

    # Chunk immutability at the database level (FR-CON-004, finding m6). Chunks of an
    # ACTIVE/SUPERSEDED version can never be updated or deleted. While the version is DRAFT,
    # an UPDATE may only fill a NULL embedding (the EMBED stage); every other column is fixed.
    op.execute(CHUNK_GUARD_FUNCTION_SQL)
    op.execute(
        "CREATE TRIGGER trg_content_chunks_guard BEFORE UPDATE OR DELETE ON content_chunks "
        "FOR EACH ROW EXECUTE FUNCTION content_chunks_guard()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_content_chunks_guard ON content_chunks")
    op.execute("DROP FUNCTION IF EXISTS content_chunks_guard()")
    op.drop_table("approved_resource_links")
    op.drop_index("ix_content_chunks_embedding_hnsw", table_name="content_chunks")
    op.drop_index("ix_content_chunks_subject_version", table_name="content_chunks")
    op.drop_table("content_chunks")
    op.drop_table("ingestion_stage_runs")
    op.drop_index("uq_one_active_version_per_asset", table_name="content_versions")
    op.drop_table("content_versions")
    op.drop_index("uq_one_syllabus_asset_per_subject", table_name="content_assets")
    op.drop_table("content_assets")
    op.drop_table("embedding_configs")
    # The `vector` extension is intentionally left installed.
