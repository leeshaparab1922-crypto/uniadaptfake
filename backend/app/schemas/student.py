from __future__ import annotations

import uuid

from pydantic import BaseModel


class StudentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    roll_number: str
    department_id: uuid.UUID
    batch_id: uuid.UUID
    section_id: uuid.UUID
    current_semester_no: int

    model_config = {"from_attributes": True}


class StudentListItemOut(StudentOut):
    """Admin list row: StudentOut plus the linked account's identity."""

    email: str
    full_name: str


class StudentListOut(BaseModel):
    items: list[StudentListItemOut]
    total: int
    limit: int
    offset: int


class ImportRowErrorOut(BaseModel):
    row_number: int
    reason: str


class ImportSummaryOut(BaseModel):
    created: int
    errors: list[ImportRowErrorOut]
