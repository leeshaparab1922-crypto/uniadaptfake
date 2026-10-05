"""NFR-AI-002 / ADR-0017: every run records prompt version FK, provider config, tokens, input refs. pg."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.ai import AgentRun, AgentRunStatus, AIProviderConfiguration, PromptVersion
from app.prompts.registry import PromptRegistryError, sync_prompts
from tests.support.curriculum_helpers import generate, prepare
from tests.support.llm import FakeLLMProvider, fixture_text

pytestmark = pytest.mark.pg


def test_run_records_prompt_version_fk_provider_config_tokens_and_input_refs(pg_session):
    setup = prepare(pg_session)
    cv, outcome = generate(pg_session, setup)
    run = pg_session.get(AgentRun, outcome.agent_run_id)
    assert run.status == AgentRunStatus.SUCCEEDED and run.attempts == 1
    assert (run.input_tokens, run.output_tokens) == (100, 200)
    assert run.input_refs["content_version_id"] == str(setup.syllabus.id)
    assert set(run.input_refs["chunk_ids"]) == {str(c) for c in setup.chunk_ids}
    cfg = pg_session.get(AIProviderConfiguration, run.provider_config_id)
    assert cfg.model == "claude-opus-5-5" and cfg.effort == "medium" and cfg.is_active
    assert run.output["topics"] and run.curriculum_version_id == cv.id


def test_agent_run_fk_resolves_prompt_text(pg_session):
    setup = prepare(pg_session)
    _cv, outcome = generate(pg_session, setup)
    run = pg_session.get(AgentRun, outcome.agent_run_id)
    prompt = pg_session.get(PromptVersion, run.prompt_version_id)
    assert prompt.agent == "curriculum" and "Curriculum Agent" in prompt.body


def test_hash_mismatch_fails_startup(pg_session, tmp_path):
    sync_prompts(pg_session)
    (tmp_path / "curriculum").mkdir()
    (tmp_path / "curriculum" / "v1.toml").write_bytes(
        b'agent = "curriculum"\nversion = 1\noutput_schema = "X"\nsystem = "edited"\nuser = "edited"\n'
    )
    with pytest.raises(PromptRegistryError, match="edited in place"):
        sync_prompts(pg_session, tmp_path)


def test_config_change_creates_new_version_and_old_runs_keep_theirs(pg_session, monkeypatch):
    from app.core.config import settings

    setup = prepare(pg_session)
    _cv, first = generate(pg_session, setup)
    monkeypatch.setattr(settings, "llm_effort", "high")
    _cv2, second = generate(pg_session, setup, llm=FakeLLMProvider(fixture_text("tie")))
    r1, r2 = (pg_session.get(AgentRun, o.agent_run_id) for o in (first, second))
    assert r1.provider_config_id != r2.provider_config_id
    configs = list(
        pg_session.scalars(select(AIProviderConfiguration).order_by(AIProviderConfiguration.config_version))
    )
    assert [c.is_active for c in configs] == [False, True] and configs[1].effort == "high"
