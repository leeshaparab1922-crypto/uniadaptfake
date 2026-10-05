"""Migration 0002 (slice 2A) on real PostgreSQL + pgvector. Marker: pg."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.pg

BACKEND = Path(__file__).resolve().parents[2]
PHASE2_TABLES = {
    "embedding_configs",
    "content_assets",
    "content_versions",
    "ingestion_stage_runs",
    "content_chunks",
    "approved_resource_links",
}


def test_phase2_tables_and_vector_extension_exist(pg_engine):
    insp = inspect(pg_engine)
    assert PHASE2_TABLES <= set(insp.get_table_names())
    with pg_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")) == 1


def test_expected_indexes_exist(pg_engine):
    with pg_engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT indexname FROM pg_indexes"))}
    assert {
        "uq_one_syllabus_asset_per_subject",
        "uq_one_active_version_per_asset",
        "ix_content_chunks_embedding_hnsw",
        "ix_content_chunks_subject_version",
    } <= names
    with pg_engine.connect() as conn:
        definition = conn.scalar(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_content_chunks_embedding_hnsw'")
        )
    assert "hnsw" in definition and "vector_cosine_ops" in definition


def test_embedding_column_is_vector_1024(pg_engine):
    with pg_engine.connect() as conn:
        typ = conn.scalar(
            text(
                "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                "WHERE attrelid = 'content_chunks'::regclass AND attname = 'embedding'"
            )
        )
    assert typ == "vector(1024)"


def test_enum_columns_are_varchar_with_named_checks_not_native_enums(pg_engine):
    with pg_engine.connect() as conn:
        native = conn.scalar(text("SELECT count(*) FROM pg_type WHERE typtype = 'e'"))
        checks = {r[0] for r in conn.execute(text("SELECT conname FROM pg_constraint WHERE contype = 'c'"))}
    assert native == 0  # ADR-0009
    assert {
        "ck_content_versions_size_bytes",
        "ck_content_versions_ext",
        "ck_content_versions_active_requires_ingested",
        "ck_content_chunks_token_count",
        "ck_content_chunks_locator_nonempty",
        "ck_approved_resource_links_https",
        "ck_embedding_configs_dimension",
    } <= checks


def test_check_constraints_reject_invalid_rows(pg_engine):
    with pg_engine.connect() as conn, pytest.raises(DBAPIError):
        conn.execute(
            text(
                "INSERT INTO embedding_configs (id, model_id, model_revision, tokenizer_revision, dimension, "
                "normalized, max_chunk_tokens, chunk_overlap_tokens) "
                "VALUES (:i, 'm', 'r', 'r', 768, true, 800, 120)"
            ),
            {"i": uuid.uuid4()},
        )


def test_upgrade_downgrade_upgrade_round_trip_on_scratch_database():
    from alembic.config import Config

    from alembic import command
    from app.core.config import settings

    base = make_url(
        os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://uniadapt:uniadapt@localhost:5432/uniadapt_test")
    )
    scratch = base.set(database="uniadapt_test_migration")
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text('DROP DATABASE IF EXISTS "uniadapt_test_migration" WITH (FORCE)'))
        conn.execute(text('CREATE DATABASE "uniadapt_test_migration"'))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    previous = settings.database_url
    settings.database_url = scratch.render_as_string(hide_password=False)
    try:
        command.upgrade(cfg, "head")
        engine = create_engine(scratch)
        assert PHASE2_TABLES <= set(inspect(engine).get_table_names())
        command.downgrade(cfg, "0001")
        assert not (PHASE2_TABLES & set(inspect(engine).get_table_names()))
        command.upgrade(cfg, "head")
        assert PHASE2_TABLES <= set(inspect(engine).get_table_names())
        engine.dispose()
    finally:
        settings.database_url = previous
        with admin.connect() as conn:
            conn.execute(text('DROP DATABASE IF EXISTS "uniadapt_test_migration" WITH (FORCE)'))
        admin.dispose()
