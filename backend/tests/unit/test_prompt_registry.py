"""Prompt registry file/hash logic (ADR-0017). The DB-backed pieces use a throwaway in-memory
SQLite database holding only the `prompt_versions` table (it has no pgvector columns); the
append-only trigger and agent_runs FK are covered by the PostgreSQL tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.ai import PromptVersion
from app.prompts.registry import (
    PromptRegistryError,
    get_prompt,
    load_prompts,
    parse_prompt,
    sync_prompts,
)

TOML = """
agent = "demo"
version = 1
output_schema = "DemoOut"
system = "You are $role"
user = "Hello $name, topics: $topics"
repair = "Fix: $errors"
"""


@pytest.fixture()
def prompts_root(tmp_path: Path) -> Path:
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "v1.toml").write_bytes((TOML).encode())
    return tmp_path


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    PromptVersion.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_real_curriculum_prompt_loads_with_hash_of_file_bytes():
    prompts = [p for p in load_prompts() if p.agent == "curriculum"]
    assert [p.version for p in prompts] == [1]
    raw = (Path(__file__).resolve().parents[2] / "app" / "prompts" / "curriculum" / "v1.toml").read_bytes()
    assert prompts[0].sha256 == hashlib.sha256(raw).hexdigest()
    assert prompts[0].output_schema == "CurriculumDraft"
    assert "$subject_code" in prompts[0].user


def test_parse_rejects_malformed_and_incomplete_files():
    with pytest.raises(PromptRegistryError):
        parse_prompt(b"this is = = not toml")
    with pytest.raises(PromptRegistryError, match="missing keys"):
        parse_prompt(b'agent = "x"\nversion = 1\n')
    with pytest.raises(PromptRegistryError):
        parse_prompt(b'agent="x"\nversion=0\noutput_schema="s"\nsystem="a"\nuser="b"\n')


def test_folder_and_file_name_must_match_contents(prompts_root: Path):
    (prompts_root / "demo" / "v2.toml").write_bytes((TOML).encode())  # says version = 1
    with pytest.raises(PromptRegistryError, match="does not match file name"):
        load_prompts(prompts_root)
    (prompts_root / "demo" / "v2.toml").unlink()
    (prompts_root / "demo" / "notes.toml").write_bytes((TOML).encode())
    assert len(load_prompts(prompts_root)) == 1  # only v<N>.toml files are prompts
    (prompts_root / "other").mkdir()
    (prompts_root / "other" / "v1.toml").write_bytes((TOML).encode())  # agent "demo" in folder "other"
    with pytest.raises(PromptRegistryError, match="does not match folder"):
        load_prompts(prompts_root)


def test_templates_render_with_standard_library_template(prompts_root: Path):
    prompt = load_prompts(prompts_root)[0]
    assert prompt.render_user(name="Ada", topics="trees") == "Hello Ada, topics: trees"
    # braces and dollar signs in injected content are not re-interpreted
    assert "$HOME" in prompt.render_user(name="$HOME", topics="{x}")
    assert prompt.render_repair(errors="e1") == "Fix: e1"


def test_sync_inserts_then_is_idempotent(db: Session, prompts_root: Path):
    first = sync_prompts(db, prompts_root)
    again = sync_prompts(db, prompts_root)
    assert [r.id for r in first] == [r.id for r in again]
    rows = list(db.scalars(select(PromptVersion)))
    assert len(rows) == 1 and rows[0].body == TOML and rows[0].output_schema == "DemoOut"
    assert rows[0].content_sha256 == hashlib.sha256(TOML.encode()).hexdigest()


def test_hash_mismatch_fails_startup(db: Session, prompts_root: Path):
    sync_prompts(db, prompts_root)
    (prompts_root / "demo" / "v1.toml").write_bytes((TOML.replace("Hello", "Hi")).encode())
    with pytest.raises(PromptRegistryError, match="edited in place"):
        sync_prompts(db, prompts_root)
    assert len(list(db.scalars(select(PromptVersion)))) == 1


def test_new_version_file_is_appended_not_edited(db: Session, prompts_root: Path):
    sync_prompts(db, prompts_root)
    (prompts_root / "demo" / "v2.toml").write_text(
        TOML.replace("version = 1", "version = 2"), encoding="utf-8"
    )
    rows = sync_prompts(db, prompts_root)
    assert sorted(r.version for r in rows) == [1, 2]


def test_get_prompt_requires_a_synced_row(db: Session, monkeypatch):
    with pytest.raises(PromptRegistryError, match="not been synced"):
        get_prompt(db, "curriculum")
    sync_prompts(db)  # the real prompts directory
    prompt, row = get_prompt(db, "curriculum")
    assert row.content_sha256 == prompt.sha256 and row.version == 1
    with pytest.raises(PromptRegistryError, match="No prompt registered"):
        get_prompt(db, "nonexistent")
