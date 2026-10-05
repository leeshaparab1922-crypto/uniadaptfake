"""Strict Pydantic output schema of the Curriculum Agent (SRS Section 18 "AI control").

This is the ONLY shape the LLM may return. Anything that does not validate here (or fails the
context checks below) goes through the bounded retry-with-repair loop and, if it still fails,
the run fails safely with no Topics created. Deterministic validation (cycles, orphans,
duplicates) happens later, in `app.services.curriculum_graph`, on data that already passed here.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.curriculum import BloomLevel, TopicClassification

EXTERNAL_REF_PREFIX = "ext:"  # "ext:<topic uuid>" = a Topic of an earlier-semester Subject


def _normalise_enum_text(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().upper().replace("-", "_").replace(" ", "_")
    return value


class DraftEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prereq_ref: str = Field(min_length=1, max_length=80)
    confidence: float = Field(ge=0.0, le=1.0)


class DraftTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    unit_order: int = Field(ge=1)  # exactly one Unit per Topic
    outcomes: list[str] = Field(min_length=1)
    bloom_level: BloomLevel
    est_hours: float = Field(gt=0, le=1000)
    classification: TopicClassification = TopicClassification.CORE
    prerequisites: list[DraftEdge] = Field(default_factory=list)
    source_chunk_ids: list[uuid.UUID] = Field(default_factory=list)
    prior_topic_id: uuid.UUID | None = None

    @field_validator("bloom_level", "classification", mode="before")
    @classmethod
    def _enum_text(cls, value: Any) -> Any:
        return _normalise_enum_text(value)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()

    @field_validator("outcomes")
    @classmethod
    def _outcomes_not_blank(cls, value: list[str]) -> list[str]:
        cleaned = [o.strip() for o in value]
        if any(not o for o in cleaned):
            raise ValueError("outcomes must not be blank")
        return cleaned


class CurriculumDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topics: list[DraftTopic] = Field(min_length=1)

    @model_validator(mode="after")
    def _keys_unique_and_edges_sane(self) -> CurriculumDraft:
        keys = [t.key for t in self.topics]
        if len(set(keys)) != len(keys):
            raise ValueError("topic keys must be unique")
        for topic in self.topics:
            seen: set[str] = set()
            for edge in topic.prerequisites:
                if edge.prereq_ref == topic.key:
                    raise ValueError(f"topic {topic.key!r} lists itself as a prerequisite")
                if edge.prereq_ref in seen:
                    raise ValueError(f"topic {topic.key!r} repeats prerequisite {edge.prereq_ref!r}")
                seen.add(edge.prereq_ref)
        return self


def validate_draft_against_context(
    draft: CurriculumDraft,
    *,
    valid_unit_orders: Collection[int],
    valid_chunk_ids: Collection[uuid.UUID],
    valid_external_refs: Collection[str],
    valid_prior_topic_ids: Collection[uuid.UUID] = (),
) -> list[str]:
    """Errors for references that point outside what the agent was given. Empty list = fine."""
    errors: list[str] = []
    keys = {t.key for t in draft.topics}
    for topic in draft.topics:
        if topic.unit_order not in valid_unit_orders:
            errors.append(
                f"topic {topic.key!r}: unit_order {topic.unit_order} is not one of the Subject's Units"
            )
        for chunk_id in topic.source_chunk_ids:
            if chunk_id not in valid_chunk_ids:
                errors.append(f"topic {topic.key!r}: unknown source_chunk_id {chunk_id}")
        if topic.prior_topic_id is not None and topic.prior_topic_id not in valid_prior_topic_ids:
            errors.append(f"topic {topic.key!r}: unknown prior_topic_id {topic.prior_topic_id}")
        for edge in topic.prerequisites:
            ref = edge.prereq_ref
            if ref in keys:
                continue
            if ref.startswith(EXTERNAL_REF_PREFIX):
                if ref not in valid_external_refs:
                    errors.append(
                        f"topic {topic.key!r}: prerequisite {ref!r} is not an offered earlier-semester Topic"
                    )
            else:
                errors.append(f"topic {topic.key!r}: prerequisite {ref!r} is not a topic key")
    return errors
