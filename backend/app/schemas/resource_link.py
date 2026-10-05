"""Schemas for recommendation-only HTTPS resource links (FR-CON-001/004, BUS-047)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.content import LinkStatus


class ResourceLinkCreate(BaseModel):
    url: str = Field(max_length=2048)
    title: str = Field(max_length=255)
    resource_type: str = Field(default="OTHER", max_length=32)
    est_minutes: int | None = Field(default=None, gt=0)
    unit_id: uuid.UUID | None = None
    topic_label: str | None = Field(default=None, max_length=255)


class ResourceLinkOut(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    topic_label: str | None
    unit_id: uuid.UUID | None
    url: str
    title: str
    resource_type: str
    est_minutes: int | None
    status: LinkStatus
    uploaded_by: uuid.UUID
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    supersedes_link_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
