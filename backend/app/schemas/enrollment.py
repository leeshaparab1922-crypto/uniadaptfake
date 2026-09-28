from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from app.models.enrollment import EnrollmentStatus


class EnrollmentOut(BaseModel):
    id: uuid.UUID
    subject_instance_id: uuid.UUID
    elective_group_id: uuid.UUID | None
    status: EnrollmentStatus
    auto_allocated: bool
    effective_from: date
    effective_to: date | None

    model_config = {"from_attributes": True}


class AssignElectiveRequest(BaseModel):
    student_id: uuid.UUID
    elective_group_id: uuid.UUID
    subject_id: uuid.UUID


class PromotionRequest(BaseModel):
    student_ids: list[uuid.UUID]
    to_batch_id: uuid.UUID
    to_semester_no: int
    to_section_id: uuid.UUID


class PromotionPreviewItemOut(BaseModel):
    student_id: uuid.UUID
    roll_number: str
    from_section_id: uuid.UUID
    to_section_id: uuid.UUID
    capacity_conflict: bool


class PromotionPreviewResponse(BaseModel):
    items: list[PromotionPreviewItemOut]
    has_conflicts: bool


class PromotionConfirmResponse(BaseModel):
    operation_id: uuid.UUID
