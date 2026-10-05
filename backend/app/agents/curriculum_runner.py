"""Runs one curriculum generation: gather inputs -> Curriculum Agent -> deterministic persist and
validation -> `agent_runs` record (FR-CUR-001, BUS-037, NFR-AI-002, NFR-REL-001).

This is the only place that joins the LLM draft to the deterministic services. The result of the
agent is data handed to `curriculum_service.persist_draft` / `validate_version`; no model output
is ever used to re-score or second-guess a validation verdict.

Idempotent: a version that is no longer GENERATING is left alone. An outage leaves the version
GENERATING with nothing partial stored and asks the caller (the Celery task) to retry.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents.curriculum_agent import (
    AGENT_NAME,
    AgentContext,
    ChunkInfo,
    CurriculumAgent,
    ExternalTopic,
    PriorTopic,
    ProviderSettings,
    UnitInfo,
)
from app.core.config import settings
from app.integrations.llm.base import LLMProvider
from app.models.ai import AgentRun, AgentRunStatus
from app.models.curriculum import CurriculumStatus, CurriculumVersion
from app.prompts.registry import get_prompt
from app.services import ai_config_service, audit
from app.services import curriculum_service as cs
from app.services import similarity_config_service as thresholds
from app.services.embedding_config_service import get_or_create_active_config
from app.services.ingestion.ports import Embedder


@dataclass(frozen=True)
class GenerationOutcome:
    curriculum_version_id: uuid.UUID
    status: str  # DRAFT | GENERATION_FAILED | RETRY | SKIPPED
    retry: bool = False
    agent_run_id: uuid.UUID | None = None
    message: str | None = None


def run_generation(
    db: Session,
    curriculum_version_id: uuid.UUID,
    *,
    provider: LLMProvider,
    embedder: Embedder,
) -> GenerationOutcome:
    cv = db.get(CurriculumVersion, curriculum_version_id)
    if cv is None or cv.status != CurriculumStatus.GENERATING:
        return GenerationOutcome(curriculum_version_id, "SKIPPED")

    inputs = cs.load_generation_inputs(db, curriculum_version_id)
    config = ai_config_service.ensure_active_config(db, AGENT_NAME)
    prompt, prompt_row = get_prompt(db, AGENT_NAME)

    run = AgentRun(
        agent=AGENT_NAME,
        provider_config_id=config.id,
        prompt_version_id=prompt_row.id,
        subject_id=cv.subject_id,
        requested_by=cv.created_by,
        curriculum_version_id=cv.id,
        # Syllabus chunk references only: no Student data ever reaches the model (NFR-SEC-011).
        input_refs={
            "content_version_id": str(inputs.content_version_id),
            "chunk_ids": [str(c.id) for c in inputs.chunks],
            "external_topic_refs": [t.ref for t in inputs.external_topics],
        },
        status=AgentRunStatus.RUNNING,
        attempts=0,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.commit()

    context = AgentContext(
        subject_code=inputs.subject.code,
        subject_name=inputs.subject.name,
        units=[UnitInfo(u.order_index, u.name, u.weightage) for u in inputs.units],
        chunks=[ChunkInfo(c.id, c.unit_no, c.locator, c.text) for c in inputs.chunks],
        external_topics=[
            ExternalTopic(t.ref, t.name, t.subject_code, t.semester_no) for t in inputs.external_topics
        ],
        prior_topics=[PriorTopic(tid, name) for tid, name in inputs.prior_topics],
    )
    agent = CurriculumAgent(provider, repair_attempts=settings.llm_repair_attempts)
    result = agent.run(
        prompt=prompt,
        settings=ProviderSettings(
            model=config.model,
            effort=config.effort,
            max_output_tokens=config.max_output_tokens,
            token_budget=config.token_budget,
        ),
        context=context,
    )

    run.status = result.status
    run.attempts = result.attempts
    run.input_tokens = result.input_tokens
    run.output_tokens = result.output_tokens
    run.error = (result.error or None) and result.error[:1000]
    run.output = result.raw_output
    run.finished_at = datetime.now(UTC)
    db.commit()

    if result.status == AgentRunStatus.QUEUED_RETRY:
        return GenerationOutcome(cv.id, "RETRY", retry=True, agent_run_id=run.id, message=result.error)
    if result.status != AgentRunStatus.SUCCEEDED or result.draft is None:
        cs.mark_generation_failed(
            db, cv.id, result.error or "Curriculum generation failed.", agent_run_id=run.id
        )
        return GenerationOutcome(cv.id, "GENERATION_FAILED", agent_run_id=run.id, message=result.error)

    try:
        # Resolve the embedding config / threshold first: creating them commits.
        thresholds.resolve_threshold(db, get_or_create_active_config(db))
        cs.persist_draft(db, cv.id, result.draft, agent_run_id=run.id)
        cs.validate_version(db, cv.id, embedder=embedder, actor=None, commit=False)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - nothing partial may survive; fail the version safely
        db.rollback()
        run_row = db.get(AgentRun, run.id)
        if run_row is not None:
            run_row.status = AgentRunStatus.FAILED
            run_row.error = f"Storing the generated curriculum failed: {type(exc).__name__}"
            db.commit()
        cs.mark_generation_failed(
            db, cv.id, "The generated curriculum could not be stored or validated.", agent_run_id=run.id
        )
        return GenerationOutcome(cv.id, "GENERATION_FAILED", agent_run_id=run.id, message=str(exc)[:500])
    audit.record(
        db,
        actor=None,
        action="CURRICULUM_GENERATION_COMPLETED",
        entity_type="curriculum_version",
        entity_id=cv.id,
        after={"agent_run_id": str(run.id), "topics": len(result.draft.topics)},
    )
    db.commit()
    return GenerationOutcome(cv.id, "DRAFT", agent_run_id=run.id)
