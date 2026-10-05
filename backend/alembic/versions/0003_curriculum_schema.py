"""Curriculum & AI schema (Phase 2, slice 2B: FR-CUR-001..004).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-04

Enums are VARCHAR + named CHECK (ADR-0009). `prompt_versions` is append-only at the database
level (ADR-0017). Seed rows (the initial 0.92 threshold, the default provider configuration,
prompt sync) are inserted by `scripts/seed_curriculum_config.py` and the startup prompt sync,
not here, because they depend on the environment (embedding revision, model choice).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROMPT_GUARD_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prompt_versions_guard() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'prompt_versions is append-only (ADR-0017)'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;
"""


def _enum(name: str, values: list[str], length: int) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=length)


def _uuid_pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _col(name: str, target: str, *, nullable: bool = False, ondelete: str = "RESTRICT") -> sa.Column:
    return sa.Column(name, sa.Uuid(), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


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


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    # --- AI provider configuration, prompt registry --------------------------------------
    op.create_table(
        "ai_provider_configurations",
        _uuid_pk(),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("provider", _enum("ai_provider", ["ANTHROPIC", "OPENAI"], 16), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("effort", sa.String(16), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("config_version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _created_at(),
        sa.UniqueConstraint("agent", "config_version", name="uq_ai_provider_config_version"),
        sa.CheckConstraint("max_output_tokens > 0 AND token_budget > 0", name="ck_ai_provider_config_tokens"),
    )
    op.create_index(
        "uq_one_active_provider_config_per_agent",
        "ai_provider_configurations",
        ["agent"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "prompt_versions",
        _uuid_pk(),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("output_schema", sa.String(128), nullable=False),
        _created_at(),
        sa.UniqueConstraint("agent", "version", name="uq_prompt_version"),
        sa.CheckConstraint("version >= 1", name="ck_prompt_versions_version"),
    )
    op.execute(PROMPT_GUARD_FUNCTION_SQL)
    op.execute(
        "CREATE TRIGGER trg_prompt_versions_guard BEFORE UPDATE OR DELETE ON prompt_versions "
        "FOR EACH ROW EXECUTE FUNCTION prompt_versions_guard()"
    )

    op.create_table(
        "agent_runs",
        _uuid_pk(),
        sa.Column("agent", sa.String(64), nullable=False),
        _col("provider_config_id", "ai_provider_configurations.id"),
        _col("prompt_version_id", "prompt_versions.id"),
        _col("subject_id", "subjects.id"),
        _col("requested_by", "users.id"),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=True),  # FK added below
        sa.Column("input_refs", sa.JSON(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            _enum("agent_run_status", ["RUNNING", "SUCCEEDED", "FAILED", "REFUSED", "QUEUED_RETRY"], 16),
            nullable=False,
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )

    # --- similarity thresholds -------------------------------------------------------------
    op.create_table(
        "similarity_thresholds",
        _uuid_pk(),
        _col("embedding_config_id", "embedding_configs.id"),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(4, 3), nullable=False),
        sa.Column(
            "status",
            _enum("threshold_status", ["DRAFT", "VALIDATED", "ACTIVE", "RETIRED"], 16),
            nullable=False,
        ),
        sa.Column("validation_report", sa.JSON(), nullable=True),
        _col("validated_by", "users.id", nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("value >= 0 AND value <= 1", name="ck_similarity_thresholds_value"),
        sa.CheckConstraint(
            "status NOT IN ('VALIDATED', 'ACTIVE') OR validated_at IS NOT NULL",
            name="ck_similarity_thresholds_validated",
        ),
    )
    op.create_index(
        "uq_one_active_threshold_per_name_config",
        "similarity_thresholds",
        ["name", "embedding_config_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    # --- curriculum ---------------------------------------------------------------------------
    op.create_table(
        "curriculum_versions",
        _uuid_pk(),
        _col("subject_id", "subjects.id"),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            _enum(
                "curriculum_status",
                ["GENERATING", "GENERATION_FAILED", "DRAFT", "ACTIVE", "SUPERSEDED", "RETURNED"],
                24,
            ),
            nullable=False,
        ),
        sa.Column("origin", _enum("curriculum_origin", ["AGENT", "FLAT_FALLBACK"], 16), nullable=False),
        _col("source_content_version_id", "content_versions.id", nullable=True),
        _col("agent_run_id", "agent_runs.id", nullable=True),
        _col("embedding_config_id", "embedding_configs.id", nullable=True),
        _col("similarity_threshold_id", "similarity_thresholds.id", nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("validated_revision", sa.Integer(), nullable=True),
        sa.Column(
            "validation_status",
            _enum("validation_status", ["NOT_RUN", "PASSED", "BLOCKED"], 16),
            nullable=False,
        ),
        sa.Column("failure_message", sa.String(1000), nullable=True),
        _col("created_by", "users.id"),
        _col("decided_by", "users.id", nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.String(1000), nullable=True),
        _col("supersedes_version_id", "curriculum_versions.id", nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("subject_id", "version_no", name="uq_curriculum_version_no_per_subject"),
        sa.CheckConstraint("revision >= 1", name="ck_curriculum_versions_revision"),
        sa.CheckConstraint(
            "status <> 'ACTIVE' OR (validation_status = 'PASSED' AND validated_revision = revision)",
            name="ck_curriculum_versions_active_validated",
        ),
    )
    op.create_index(
        "uq_one_active_curriculum_per_subject",
        "curriculum_versions",
        ["subject_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_foreign_key(
        "fk_agent_runs_cv",
        "agent_runs",
        "curriculum_versions",
        ["curriculum_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "topics",
        _uuid_pk(),
        _col("subject_id", "subjects.id"),
        _created_at(),
    )

    op.create_table(
        "topic_versions",
        _uuid_pk(),
        _col("topic_id", "topics.id"),
        _col("curriculum_version_id", "curriculum_versions.id"),
        _col("unit_id", "units.id", nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("outcomes", sa.JSON(), nullable=False),
        sa.Column(
            "bloom_level",
            _enum(
                "bloom_level",
                ["REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE"],
                16,
            ),
            nullable=False,
        ),
        sa.Column("est_hours", sa.Numeric(6, 2), nullable=False),
        sa.Column(
            "classification",
            _enum("topic_classification", ["CORE", "OPTIONAL", "SELF_STUDY"], 16),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        _col("embedding_config_id", "embedding_configs.id", nullable=True),
        sa.Column("embedding_text_sha256", sa.String(64), nullable=True),
        sa.UniqueConstraint("curriculum_version_id", "topic_id", name="uq_topic_per_curriculum_version"),
        sa.CheckConstraint("est_hours > 0", name="ck_topic_versions_est_hours"),
    )
    op.create_index("ix_topic_versions_cv", "topic_versions", ["curriculum_version_id"])

    op.create_table(
        "topic_prereqs",
        _uuid_pk(),
        _col("curriculum_version_id", "curriculum_versions.id"),
        _col("topic_id", "topics.id"),
        _col("prereq_topic_id", "topics.id"),
        _col("prereq_curriculum_version_id", "curriculum_versions.id", nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("approved_by_teacher", sa.Boolean(), nullable=False),
        sa.Column("source", _enum("edge_source", ["AGENT", "TEACHER"], 16), nullable=False),
        sa.Column("dropped", sa.Boolean(), nullable=False),
        sa.Column("drop_reason", sa.String(500), nullable=True),
        sa.UniqueConstraint(
            "curriculum_version_id", "topic_id", "prereq_topic_id", name="uq_topic_prereq_edge"
        ),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_topic_prereqs_confidence"),
        sa.CheckConstraint("topic_id <> prereq_topic_id", name="ck_topic_prereqs_not_self"),
    )

    op.create_table(
        "topic_mappings",
        _uuid_pk(),
        _col("curriculum_version_id", "curriculum_versions.id"),
        sa.Column("kind", _enum("mapping_kind", ["RENAME", "MERGE", "SPLIT"], 16), nullable=False),
        _col("from_topic_id", "topics.id"),
        _col("to_topic_id", "topics.id"),
        _col("created_by", "users.id"),
        _created_at(),
    )

    op.create_table(
        "graph_validation_flags",
        _uuid_pk(),
        _col("curriculum_version_id", "curriculum_versions.id"),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            _enum(
                "flag_kind",
                ["CYCLE_EDGE_DROPPED", "CYCLE_REMAINING", "ORPHAN", "DUPLICATE_TOPIC", "SCOPE_VIOLATION"],
                24,
            ),
            nullable=False,
        ),
        _col("topic_id", "topics.id", nullable=True),
        _col("other_topic_id", "topics.id", nullable=True),
        _col("edge_id", "topic_prereqs.id", nullable=True, ondelete="SET NULL"),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("blocking", sa.Boolean(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_graph_flags_cv", "graph_validation_flags", ["curriculum_version_id"])

    op.create_table(
        "topic_source_chunks",
        _col("topic_version_id", "topic_versions.id", ondelete="CASCADE"),
        _col("content_chunk_id", "content_chunks.id"),
        sa.PrimaryKeyConstraint("topic_version_id", "content_chunk_id"),
    )


def downgrade() -> None:
    op.drop_table("topic_source_chunks")
    op.drop_index("ix_graph_flags_cv", table_name="graph_validation_flags")
    op.drop_table("graph_validation_flags")
    op.drop_table("topic_mappings")
    op.drop_table("topic_prereqs")
    op.drop_index("ix_topic_versions_cv", table_name="topic_versions")
    op.drop_table("topic_versions")
    op.drop_table("topics")
    op.drop_constraint("fk_agent_runs_cv", "agent_runs", type_="foreignkey")
    op.drop_index("uq_one_active_curriculum_per_subject", table_name="curriculum_versions")
    op.drop_table("curriculum_versions")
    op.drop_index("uq_one_active_threshold_per_name_config", table_name="similarity_thresholds")
    op.drop_table("similarity_thresholds")
    op.drop_table("agent_runs")
    op.execute("DROP TRIGGER IF EXISTS trg_prompt_versions_guard ON prompt_versions")
    op.execute("DROP FUNCTION IF EXISTS prompt_versions_guard()")
    op.drop_table("prompt_versions")
    op.drop_index("uq_one_active_provider_config_per_agent", table_name="ai_provider_configurations")
    op.drop_table("ai_provider_configurations")
