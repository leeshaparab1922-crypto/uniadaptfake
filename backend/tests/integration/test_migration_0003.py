"""Migration 0003 (slice 2B) on real PostgreSQL + pgvector. Marker: pg."""

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
TABLES = {
    "ai_provider_configurations",
    "prompt_versions",
    "agent_runs",
    "similarity_thresholds",
    "curriculum_versions",
    "topics",
    "topic_versions",
    "topic_prereqs",
    "topic_mappings",
    "graph_validation_flags",
    "topic_source_chunks",
}


def test_tables_and_indexes_exist(pg_engine):
    assert TABLES <= set(inspect(pg_engine).get_table_names())
    with pg_engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT indexname FROM pg_indexes"))}
    assert {
        "uq_one_active_curriculum_per_subject",
        "uq_one_active_provider_config_per_agent",
        "uq_one_active_threshold_per_name_config",
    } <= names


def test_topic_embedding_is_vector_1024(pg_engine):
    with pg_engine.connect() as conn:
        typ = conn.scalar(
            text(
                "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                "WHERE attrelid = 'topic_versions'::regclass AND attname = 'embedding'"
            )
        )
    assert typ == "vector(1024)"


def test_enums_are_varchar_with_named_checks(pg_engine):
    with pg_engine.connect() as conn:
        native = conn.scalar(text("SELECT count(*) FROM pg_type WHERE typtype = 'e'"))
        checks = {r[0] for r in conn.execute(text("SELECT conname FROM pg_constraint WHERE contype = 'c'"))}
    assert native == 0
    assert {
        "curriculum_status",
        "flag_kind",
        "ck_topic_versions_est_hours",
        "ck_topic_prereqs_confidence",
        "ck_topic_prereqs_not_self",
        "ck_curriculum_versions_active_validated",
        "ck_similarity_thresholds_validated",
    } <= checks


def test_prompt_versions_is_append_only(pg_engine):
    pid = uuid.uuid4()
    with pg_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO prompt_versions (id, agent, version, content_sha256, body, output_schema) "
                "VALUES (:i, 'x', 1, 'h', 'b', 's')"
            ),
            {"i": pid},
        )
    for sql in (
        "UPDATE prompt_versions SET body = 'changed' WHERE id = :i",
        "DELETE FROM prompt_versions WHERE id = :i",
    ):
        with pytest.raises(DBAPIError), pg_engine.begin() as conn:
            conn.execute(text(sql), {"i": pid})
    with pg_engine.begin() as conn:  # TRUNCATE is not a row-level operation; test cleanup only
        conn.execute(text("TRUNCATE prompt_versions CASCADE"))


def test_upgrade_downgrade_upgrade_round_trip_0003():
    from alembic.config import Config

    from alembic import command
    from app.core.config import settings

    base = make_url(
        os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://uniadapt:uniadapt@localhost:5432/uniadapt_test")
    )
    scratch = base.set(database="uniadapt_test_migration3")
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text('DROP DATABASE IF EXISTS "uniadapt_test_migration3" WITH (FORCE)'))
        conn.execute(text('CREATE DATABASE "uniadapt_test_migration3"'))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    previous = settings.database_url
    settings.database_url = scratch.render_as_string(hide_password=False)
    try:
        command.upgrade(cfg, "head")
        engine = create_engine(scratch)
        assert TABLES <= set(inspect(engine).get_table_names())
        command.downgrade(cfg, "0002")
        assert not (TABLES & set(inspect(engine).get_table_names()))
        command.upgrade(cfg, "head")
        assert TABLES <= set(inspect(engine).get_table_names())
        engine.dispose()
    finally:
        settings.database_url = previous
        with admin.connect() as conn:
            conn.execute(text('DROP DATABASE IF EXISTS "uniadapt_test_migration3" WITH (FORCE)'))
        admin.dispose()
