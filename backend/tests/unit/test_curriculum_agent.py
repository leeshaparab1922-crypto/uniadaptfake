"""Curriculum Agent with a fake provider (FR-CUR-001). No network, no key."""

from __future__ import annotations

import json
import uuid

import pytest
from pydantic import ValidationError

from app.agents.curriculum_agent import (
    AgentContext,
    ChunkInfo,
    CurriculumAgent,
    ExternalTopic,
    ProviderSettings,
    UnitInfo,
)
from app.integrations.llm.base import LLMConfigurationError, LLMResponse, LLMUnavailableError
from app.models.ai import AgentRunStatus
from app.prompts.registry import load_prompts
from app.schemas.curriculum_agent import CurriculumDraft
from tests.support.llm import FakeLLMProvider, fixture_json, fixture_text

SETTINGS = ProviderSettings(
    model="claude-opus-5-5", effort="medium", max_output_tokens=1000, token_budget=10_000
)
CHUNK = uuid.uuid4()
CONTEXT = AgentContext(
    subject_code="CS301",
    subject_name="Data Structures",
    units=[UnitInfo(1, "Basics", 34), UnitInfo(2, "Trees", 33), UnitInfo(3, "Graphs", 33)],
    chunks=[ChunkInfo(CHUNK, 1, "page:1", "Unit 1 Arrays and linked lists")],
)
PROMPT = next(p for p in load_prompts() if p.agent == "curriculum")


def run(provider, *, repair=2, settings=SETTINGS, context=CONTEXT):
    return CurriculumAgent(provider, repair_attempts=repair).run(
        prompt=PROMPT, settings=settings, context=context
    )


def test_valid_output_accepted():
    provider = FakeLLMProvider(fixture_text("valid"))
    result = run(provider)
    assert result.status == AgentRunStatus.SUCCEEDED
    assert [t.key for t in result.draft.topics] == ["a", "b"]
    # enum text is normalised: "Apply" -> APPLY, "Self-study" -> SELF_STUDY
    assert result.draft.topics[0].bloom_level.value == "APPLY"
    assert result.draft.topics[1].classification.value == "SELF_STUDY"
    assert result.input_tokens == 100 and result.output_tokens == 200 and result.attempts == 1


def test_request_carries_prompt_schema_and_settings():
    provider = FakeLLMProvider(fixture_text("valid"))
    run(provider)
    req = provider.requests[0]
    assert req.system == PROMPT.system
    assert "CS301" in req.user and str(CHUNK) in req.user
    assert req.model == "claude-opus-5-5" and req.effort == "medium"
    assert "topics" in req.json_schema["properties"]


def test_schema_violation_triggers_repair_then_succeeds():
    provider = FakeLLMProvider(fixture_text("schema_broken"), fixture_text("valid"))
    result = run(provider)
    assert result.status == AgentRunStatus.SUCCEEDED
    assert result.attempts == 2
    assert "rejected" in provider.requests[1].user  # the repair instruction with the reasons was added


def test_non_json_output_is_repaired():
    provider = FakeLLMProvider("here is your curriculum!", fixture_text("valid"))
    assert run(provider).status == AgentRunStatus.SUCCEEDED


def test_repair_exhausted_fails_safely_no_topics_created():
    provider = FakeLLMProvider(*[fixture_text("schema_broken")] * 3)
    result = run(provider, repair=2)
    assert result.status == AgentRunStatus.FAILED
    assert result.draft is None
    assert result.attempts == 3
    assert "schema" in result.error


def test_no_repair_budget_means_single_attempt():
    provider = FakeLLMProvider(fixture_text("schema_broken"))
    result = run(provider, repair=0)
    assert result.status == AgentRunStatus.FAILED and result.attempts == 1


def test_llm_outage_queues_retry_status_not_partial_draft():
    result = run(FakeLLMProvider(LLMUnavailableError("down")))
    assert result.status == AgentRunStatus.QUEUED_RETRY
    assert result.draft is None


def test_refusal_stop_reason_marks_run_refused_no_graph():
    refusal = LLMResponse(text="", stop_reason="refusal", input_tokens=10, output_tokens=0)
    provider = FakeLLMProvider(refusal, fixture_text("valid"))
    result = run(provider)
    assert result.status == AgentRunStatus.REFUSED
    assert result.draft is None
    assert len(provider.requests) == 1  # a refusal is never "repaired" into an empty/other graph


def test_configuration_error_is_failed_not_retry():
    result = run(FakeLLMProvider(LLMConfigurationError("no key")))
    assert result.status == AgentRunStatus.FAILED and "no key" in result.error


def test_token_budget_stops_further_attempts():
    tiny = ProviderSettings(model="m", effort="medium", max_output_tokens=10, token_budget=250)
    provider = FakeLLMProvider(
        fixture_text("schema_broken"), fixture_text("schema_broken"), fixture_text("valid")
    )
    result = run(provider, settings=tiny)
    assert result.status == AgentRunStatus.FAILED
    assert "token budget" in result.error
    assert len(provider.requests) == 1  # 300 tokens used >= 250 budget: no further attempt


def test_confidence_out_of_range_rejected():
    data = fixture_json("valid")
    data["topics"][1]["prerequisites"][0]["confidence"] = 1.5
    with pytest.raises(ValidationError):
        CurriculumDraft.model_validate(data)


def test_invalid_bloom_rejected():
    data = fixture_json("valid")
    data["topics"][0]["bloom_level"] = "MEMORISE"
    with pytest.raises(ValidationError):
        CurriculumDraft.model_validate(data)


def test_est_hours_nonpositive_rejected():
    for hours in (0, -2):
        data = fixture_json("valid")
        data["topics"][0]["est_hours"] = hours
        with pytest.raises(ValidationError):
            CurriculumDraft.model_validate(data)


def test_topic_with_two_units_or_none_rejected():
    data = fixture_json("valid")
    data["topics"][0]["unit_order"] = [1, 2]
    with pytest.raises(ValidationError):
        CurriculumDraft.model_validate(data)
    data = fixture_json("valid")
    del data["topics"][0]["unit_order"]
    with pytest.raises(ValidationError):
        CurriculumDraft.model_validate(data)


def test_empty_outcomes_and_unknown_fields_rejected():
    data = fixture_json("valid")
    data["topics"][0]["outcomes"] = []
    with pytest.raises(ValidationError):
        CurriculumDraft.model_validate(data)
    data = fixture_json("valid")
    data["topics"][0]["exam_weight"] = 20  # exam weightage is inherited from the Unit, never invented
    with pytest.raises(ValidationError):
        CurriculumDraft.model_validate(data)


def test_self_prerequisite_and_duplicate_keys_rejected():
    data = fixture_json("valid")
    data["topics"][0]["prerequisites"] = [{"prereq_ref": "a", "confidence": 0.5}]
    with pytest.raises(ValidationError):
        CurriculumDraft.model_validate(data)
    data = fixture_json("valid")
    data["topics"][1]["key"] = "a"
    with pytest.raises(ValidationError):
        CurriculumDraft.model_validate(data)


def test_unit_order_outside_the_subject_is_repaired():
    bad = fixture_json("valid")
    bad["topics"][0]["unit_order"] = 9
    provider = FakeLLMProvider(json.dumps(bad), fixture_text("valid"))
    result = run(provider)
    assert result.status == AgentRunStatus.SUCCEEDED and result.attempts == 2
    assert "unit_order 9" in provider.requests[1].user


def test_unknown_chunk_and_prerequisite_refs_rejected_then_failed():
    bad = fixture_json("valid")
    bad["topics"][0]["source_chunk_ids"] = [str(uuid.uuid4())]
    bad["topics"][1]["prerequisites"] = [{"prereq_ref": "ext:" + str(uuid.uuid4()), "confidence": 0.5}]
    result = run(FakeLLMProvider(*[json.dumps(bad)] * 3))
    assert result.status == AgentRunStatus.FAILED


def test_offered_external_prerequisite_is_accepted():
    ext = ExternalTopic(f"ext:{uuid.uuid4()}", "Discrete Sets", "MA201", 2)
    context = AgentContext(
        subject_code="CS301",
        subject_name="DS",
        units=CONTEXT.units,
        chunks=CONTEXT.chunks,
        external_topics=[ext],
    )
    data = fixture_json("valid")
    data["topics"][1]["prerequisites"].append({"prereq_ref": ext.ref, "confidence": 0.6})
    data["topics"][0]["source_chunk_ids"] = [str(CHUNK)]
    result = run(FakeLLMProvider(json.dumps(data)), context=context)
    assert result.status == AgentRunStatus.SUCCEEDED
