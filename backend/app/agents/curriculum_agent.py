"""Curriculum Agent: LLM drafting + bounded retry-with-repair (FR-CUR-001, Section 18 "AI control").

Coordination only (plan P-14: plain provider call + a Python loop, no LangGraph in Phase 2).
The agent returns a schema-valid `CurriculumDraft` or a failure; it never validates graph
semantics (cycles/orphans/duplicates) - that is deterministic code in
`app.services.curriculum_graph` and runs on the draft afterwards. Repair applies only to
schema-invalid output, never to a validation verdict.

Outcomes:
* SUCCEEDED   - a draft that passed the Pydantic schema and context checks.
* REFUSED     - the provider returned the `refusal` stop reason (ADR-0016): failed run, no graph.
* QUEUED_RETRY- the provider is unreachable (ASM-004): nothing partial is kept, the task retries.
* FAILED      - repair attempts or the token budget are exhausted, or the provider/config failed.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.integrations.llm.base import (
    LLMConfigurationError,
    LLMError,
    LLMProvider,
    LLMRequest,
    LLMUnavailableError,
)
from app.models.ai import AgentRunStatus
from app.prompts.registry import PromptFile
from app.schemas.curriculum_agent import (
    EXTERNAL_REF_PREFIX,
    CurriculumDraft,
    validate_draft_against_context,
)

AGENT_NAME = "curriculum"


@dataclass(frozen=True)
class UnitInfo:
    order_index: int
    name: str
    weightage: int


@dataclass(frozen=True)
class ChunkInfo:
    chunk_id: uuid.UUID
    unit_no: int | None
    locator: str
    text: str


@dataclass(frozen=True)
class ExternalTopic:
    ref: str  # "ext:<topic uuid>"
    name: str
    subject_code: str
    semester_no: int


@dataclass(frozen=True)
class PriorTopic:
    topic_id: uuid.UUID
    name: str


@dataclass(frozen=True)
class AgentContext:
    subject_code: str
    subject_name: str
    units: Sequence[UnitInfo]
    chunks: Sequence[ChunkInfo]
    external_topics: Sequence[ExternalTopic] = ()
    prior_topics: Sequence[PriorTopic] = ()


@dataclass(frozen=True)
class ProviderSettings:
    model: str
    effort: str
    max_output_tokens: int
    token_budget: int


@dataclass
class AgentResult:
    status: AgentRunStatus
    draft: CurriculumDraft | None = None
    attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    raw_output: dict[str, Any] | None = None
    stop_reasons: list[str | None] = field(default_factory=list)


def _units_text(units: Sequence[UnitInfo]) -> str:
    return "\n".join(f"{u.order_index}. {u.name} ({u.weightage}%)" for u in units) or "(none)"


def _chunks_text(chunks: Sequence[ChunkInfo]) -> str:
    return "\n\n".join(
        f"[{c.chunk_id} | unit {c.unit_no if c.unit_no is not None else '?'} | {c.locator}]\n{c.text}"
        for c in chunks
    )


def _external_text(topics: Sequence[ExternalTopic]) -> str:
    return (
        "\n".join(f"{t.ref}: {t.name} ({t.subject_code}, semester {t.semester_no})" for t in topics)
        or "(none offered)"
    )


def _prior_text(topics: Sequence[PriorTopic]) -> str:
    return "\n".join(f"{t.topic_id}: {t.name}" for t in topics) or "(none)"


def _parse(text: str) -> tuple[CurriculumDraft | None, list[str], dict[str, Any] | None]:
    """Parse and validate model output. Returns (draft, errors, parsed_json_if_any)."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        return None, [f"The output is not valid JSON: {exc}"], None
    try:
        draft = CurriculumDraft.model_validate(parsed)
    except ValidationError as exc:
        errors = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:25]]
        return None, errors, parsed if isinstance(parsed, dict) else None
    return draft, [], parsed


class CurriculumAgent:
    def __init__(self, provider: LLMProvider, *, repair_attempts: int) -> None:
        self._provider = provider
        self._repair_attempts = max(0, repair_attempts)

    def run(self, *, prompt: PromptFile, settings: ProviderSettings, context: AgentContext) -> AgentResult:
        schema = CurriculumDraft.model_json_schema()
        user = prompt.render_user(
            subject_code=context.subject_code,
            subject_name=context.subject_name,
            units=_units_text(context.units),
            syllabus_chunks=_chunks_text(context.chunks),
            earlier_topics=_external_text(context.external_topics),
            prior_topics=_prior_text(context.prior_topics),
        )
        result = AgentResult(status=AgentRunStatus.RUNNING)
        valid_units = {u.order_index for u in context.units}
        valid_chunks = {c.chunk_id for c in context.chunks}
        valid_external = {t.ref for t in context.external_topics}
        valid_prior = {t.topic_id for t in context.prior_topics}

        pending_user = user
        max_calls = 1 + self._repair_attempts
        for _ in range(max_calls):
            if result.input_tokens + result.output_tokens >= settings.token_budget:
                result.status = AgentRunStatus.FAILED
                result.error = "The AI token budget for this run was exhausted before a valid draft."
                return result
            request = LLMRequest(
                system=prompt.system,
                user=pending_user,
                json_schema=schema,
                model=settings.model,
                effort=settings.effort,
                max_output_tokens=settings.max_output_tokens,
            )
            result.attempts += 1
            try:
                response = self._provider.generate_structured(request)
            except LLMUnavailableError:
                # ASM-004: keep nothing partial; the worker retries later.
                result.status = AgentRunStatus.QUEUED_RETRY
                result.error = "The AI provider is unavailable; generation is queued and will be retried."
                return result
            except LLMConfigurationError as exc:
                result.status = AgentRunStatus.FAILED
                result.error = str(exc)
                return result
            except LLMError as exc:
                result.status = AgentRunStatus.FAILED
                result.error = str(exc)
                return result

            result.input_tokens += response.input_tokens
            result.output_tokens += response.output_tokens
            result.stop_reasons.append(response.stop_reason)
            if response.refused:
                result.status = AgentRunStatus.REFUSED
                result.error = "The AI provider declined to produce a curriculum for this content."
                return result

            draft, errors, parsed = _parse(response.text)
            result.raw_output = parsed
            if draft is not None:
                errors = validate_draft_against_context(
                    draft,
                    valid_unit_orders=valid_units,
                    valid_chunk_ids=valid_chunks,
                    valid_external_refs=valid_external,
                    valid_prior_topic_ids=valid_prior,
                )
            if draft is not None and not errors:
                result.status = AgentRunStatus.SUCCEEDED
                result.draft = draft
                return result

            # Schema-invalid: bounded repair using the original request plus the rejection reasons.
            error_text = "\n".join(f"- {e}" for e in errors)
            pending_user = f"{user}\n\n{prompt.render_repair(errors=error_text)}"
            result.error = "; ".join(errors[:5])

        result.status = AgentRunStatus.FAILED
        result.draft = None
        result.error = "The AI output did not match the required schema after repair attempts: " + (
            result.error or "unknown error"
        )
        return result


__all__ = [
    "AGENT_NAME",
    "EXTERNAL_REF_PREFIX",
    "AgentContext",
    "AgentResult",
    "ChunkInfo",
    "CurriculumAgent",
    "ExternalTopic",
    "PriorTopic",
    "ProviderSettings",
    "UnitInfo",
]
