"""Request/response schemas for Teacher curriculum endpoints G1..G15 (FR-CUR-001..004)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.ai import AgentRunStatus
from app.models.curriculum import (
    BloomLevel,
    CurriculumOrigin,
    CurriculumStatus,
    EdgeSource,
    FlagKind,
    MappingKind,
    ThresholdStatus,
    TopicClassification,
    ValidationStatus,
)


class CurriculumVersionOut(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    version_no: int
    status: CurriculumStatus
    origin: CurriculumOrigin
    revision: int
    validated_revision: int | None
    validation_status: ValidationStatus
    failure_message: str | None
    source_content_version_id: uuid.UUID | None
    agent_run_id: uuid.UUID | None
    supersedes_version_id: uuid.UUID | None
    decided_at: datetime | None
    decision_reason: str | None
    activated_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnitOut(BaseModel):
    id: uuid.UUID
    order_index: int
    name: str
    weightage: int

    model_config = ConfigDict(from_attributes=True)


class TopicOut(BaseModel):
    topic_id: uuid.UUID
    name: str
    unit_id: uuid.UUID | None
    unit_weightage: int | None  # derived from the Unit; never stored on the Topic
    outcomes: list[str]
    bloom_level: BloomLevel
    est_hours: float
    classification: TopicClassification
    order_index: int
    source_chunk_ids: list[uuid.UUID]
    is_orphan: bool


class EdgeOut(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    prereq_topic_id: uuid.UUID
    confidence: float
    source: EdgeSource
    approved_by_teacher: bool
    dropped: bool
    drop_reason: str | None
    cross_subject: bool
    prereq_curriculum_version_id: uuid.UUID | None
    external_subject_code: str | None
    external_topic_name: str | None


class FlagOut(BaseModel):
    id: uuid.UUID
    kind: FlagKind
    topic_id: uuid.UUID | None
    other_topic_id: uuid.UUID | None
    edge_id: uuid.UUID | None
    detail: dict | None
    blocking: bool
    revision: int

    model_config = ConfigDict(from_attributes=True)


class MappingOut(BaseModel):
    kind: MappingKind
    from_topic_id: uuid.UUID
    to_topic_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class AgentRunOut(BaseModel):
    id: uuid.UUID
    status: AgentRunStatus
    attempts: int
    input_tokens: int
    output_tokens: int
    error: str | None
    prompt_version_id: uuid.UUID
    provider_config_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class ThresholdOut(BaseModel):
    id: uuid.UUID
    value: float
    status: ThresholdStatus
    validated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class EmbeddingConfigOut(BaseModel):
    id: uuid.UUID
    model_id: str
    model_revision: str

    model_config = ConfigDict(from_attributes=True)


class CurriculumGraphOut(BaseModel):
    version: CurriculumVersionOut
    units: list[UnitOut]
    topics: list[TopicOut]
    edges: list[EdgeOut]
    flags: list[FlagOut]
    mappings: list[MappingOut]
    agent_run: AgentRunOut | None
    threshold: ThresholdOut | None
    embedding_config: EmbeddingConfigOut | None
    approval_blockers: list[str]
    can_approve: bool
    is_owner: bool
    banner: str | None  # Section 37 "Cyclic prerequisite graph" message when an edge was dropped


class ValidationOut(BaseModel):
    revision: int
    passed: bool
    dropped_edges: int
    orphans: int
    duplicates: int
    blocking_reasons: list[str]
    banner: str | None


class DecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class TopicPatch(BaseModel):
    """Only the fields that are present are changed."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    classification: TopicClassification | None = None
    est_hours: float | None = Field(default=None, gt=0, le=1000)
    outcomes: list[str] | None = Field(default=None, min_length=1, max_length=50)
    bloom_level: BloomLevel | None = None
    unit_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _no_explicit_nulls(self) -> TopicPatch:
        """Every Topic field is required on the Topic, so a field sent as null is invalid input
        (finding D2): omit a field to leave it unchanged."""
        nulls = sorted(f for f in self.model_fields_set if getattr(self, f) is None)
        if nulls:
            raise ValueError(f"Fields cannot be null: {', '.join(nulls)}. Omit a field to keep it.")
        return self


class MergeRequest(BaseModel):
    topic_ids: list[uuid.UUID] = Field(min_length=2, max_length=20)
    target_topic_id: uuid.UUID
    name: str | None = Field(default=None, max_length=255)


class SplitPartIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    outcomes: list[str] | None = Field(default=None, min_length=1)
    est_hours: float | None = Field(default=None, gt=0, le=1000)
    prereq_topic_ids: list[uuid.UUID] = Field(default_factory=list)
    dependent_topic_ids: list[uuid.UUID] = Field(default_factory=list)


class SplitRequest(BaseModel):
    parts: list[SplitPartIn] = Field(min_length=2, max_length=10)


class ReorderRequest(BaseModel):
    topic_ids: list[uuid.UUID] = Field(min_length=1)


class EdgeCreate(BaseModel):
    topic_id: uuid.UUID
    prereq_topic_id: uuid.UUID
    confidence: float = Field(default=1.0, ge=0, le=1)
    prereq_curriculum_version_id: uuid.UUID | None = None
