from __future__ import annotations

import uuid
from datetime import date, time

from pydantic import BaseModel, Field

from app.models.calendar import SlotType


class AcademicCalendarCreate(BaseModel):
    semester_id: uuid.UUID
    holidays: list[str] = Field(default_factory=list)
    ia_window_start: date
    ia_window_end: date
    practical_window_start: date
    practical_window_end: date
    university_exam_window_start: date
    university_exam_window_end: date


class AcademicCalendarOut(BaseModel):
    id: uuid.UUID
    semester_id: uuid.UUID
    version: int
    holidays: list[str]
    ia_window_start: date
    ia_window_end: date
    practical_window_start: date
    practical_window_end: date
    university_exam_window_start: date
    university_exam_window_end: date

    model_config = {"from_attributes": True}


class ExamDateSetRequest(BaseModel):
    subject_instance_id: uuid.UUID
    exam_date: date
    calendar_id: uuid.UUID


class TimetableSlotCreate(BaseModel):
    section_id: uuid.UUID
    subject_instance_id: uuid.UUID | None = None
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    type: SlotType
    effective_from: date
    effective_to: date | None = None


class TimetableSlotOut(BaseModel):
    id: uuid.UUID
    section_id: uuid.UUID
    subject_instance_id: uuid.UUID | None
    day_of_week: int
    start_time: time
    end_time: time
    type: SlotType
    effective_from: date
    effective_to: date | None

    model_config = {"from_attributes": True}
