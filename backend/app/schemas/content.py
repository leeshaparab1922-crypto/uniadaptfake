"""Request/response schemas for Teacher content endpoints (FR-CON-001..004)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.content import (
    ContentType,
    ContentVersionStatus,
    IngestionStage,
    IngestionStatus,
    LocatorType,
    StageStatus,
)


class UnitBrief(BaseModel):
    id: uuid.UUID
    order_index: int
    name: str
    weightage: int

    model_config = {"from_attributes": True}


class AssignedSubjectOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    semester_no: int
    is_owner: bool
    units: list[UnitBrief]


class StageRunOut(BaseModel):
    stage: IngestionStage
    attempt: int
    status: StageStatus
    started_at: datetime
    finished_at: datetime | None
    detail: dict | None
    error: str | None

    model_config = {"from_attributes": True}


class ContentVersionOut(BaseModel):
    id: uuid.UUID
    content_asset_id: uuid.UUID
    version_no: int
    status: ContentVersionStatus
    ingestion_status: IngestionStatus
    failed_stage: str | None
    failure_message: str | None
    unit_id: uuid.UUID | None
    original_filename: str
    ext: str
    mime_type: str
    size_bytes: int
    sha256: str
    embedding_config_id: uuid.UUID | None
    uploaded_by: uuid.UUID
    activated_by: uuid.UUID | None
    activated_at: datetime | None
    supersedes_version_id: uuid.UUID | None
    created_at: datetime
    ingestion_heartbeat_at: datetime | None = None
    # Filled by the route from content_service.retry_state (finding M2).
    can_retry: bool = False
    retry_available_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContentVersionDetailOut(ContentVersionOut):
    content_type: ContentType
    asset_title: str
    subject_id: uuid.UUID
    chunk_count: int
    stage_runs: list[StageRunOut]


class ContentAssetOut(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    content_type: ContentType
    title: str
    versions: list[ContentVersionOut]


class ChunkOut(BaseModel):
    """Chunk metadata (vectors are never returned)."""

    id: uuid.UUID
    subject_id: uuid.UUID
    content_version_id: uuid.UUID
    unit_no: int | None
    source_file: str
    locator_type: LocatorType
    locator: str
    page_no: int | None
    chunk_type: ContentType
    chunk_index: int
    text: str
    token_count: int
    embedding_config_id: uuid.UUID

    model_config = {"from_attributes": True}


class ChunkReferenceOut(BaseModel):
    """An immutable chunk reference resolved to its version, file and locator."""

    chunk: ChunkOut
    content_version_id: uuid.UUID
    version_no: int
    version_status: ContentVersionStatus
    content_asset_id: uuid.UUID
    source_file: str
    locator: str


class DecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RollbackRequest(DecisionRequest):
    target_version_id: uuid.UUID
