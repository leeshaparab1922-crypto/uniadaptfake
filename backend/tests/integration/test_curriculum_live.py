"""One real generation against the Anthropic API. Skipped unless ANTHROPIC_API_KEY is set."""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = [
    pytest.mark.llm_live,
    pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set"),
]


def test_live_curriculum_generation_smoke(monkeypatch):
    from app.agents.curriculum_agent import (
        AgentContext,
        ChunkInfo,
        CurriculumAgent,
        ProviderSettings,
        UnitInfo,
    )
    from app.core.config import settings
    from app.integrations.llm.anthropic_adapter import AnthropicAdapter
    from app.models.ai import AgentRunStatus
    from app.prompts.registry import load_prompts

    monkeypatch.setattr(settings, "anthropic_api_key", os.environ["ANTHROPIC_API_KEY"])
    ctx = AgentContext(
        "CS301",
        "Data Structures",
        [UnitInfo(1, "Basics", 100)],
        [ChunkInfo(uuid.uuid4(), 1, "page:1", "Unit 1: arrays, linked lists, stacks and queues.")],
    )
    prompt = next(p for p in load_prompts() if p.agent == "curriculum")
    result = CurriculumAgent(AnthropicAdapter(), repair_attempts=1).run(
        prompt=prompt,
        settings=ProviderSettings(settings.llm_model, settings.llm_effort, 8000, 100000),
        context=ctx,
    )
    assert result.status == AgentRunStatus.SUCCEEDED and result.draft.topics
