from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.subject_instance import SubjectInstanceStatus, TeacherAssignmentRole


class SubjectInstanceCreate(BaseModel):
    subject_id: uuid.UUID
    section_id: uuid.UUID


class SubjectInstanceOut(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    section_id: uuid.UUID
    exam_at: datetime | None
    status: SubjectInstanceStatus

    model_config = {"from_attributes": True}


class TeacherAssignmentCreate(BaseModel):
    teacher_id: uuid.UUID
    subject_instance_id: uuid.UUID
    role: TeacherAssignmentRole


class TeacherAssignmentOut(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    subject_instance_id: uuid.UUID
    role: TeacherAssignmentRole

    model_config = {"from_attributes": True}


class SubjectOwnerSetRequest(BaseModel):
    subject_id: uuid.UUID
    owner_teacher_id: uuid.UUID
    reason: str | None = None


class SubjectOwnerOut(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    owner_teacher_id: uuid.UUID

    model_config = {"from_attributes": True}
