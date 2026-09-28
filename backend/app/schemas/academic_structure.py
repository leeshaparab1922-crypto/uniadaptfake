from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field


class InstituteCreate(BaseModel):
    name: str = Field(min_length=1)
    timezone: str = Field(min_length=1, default="Asia/Kolkata")


class InstituteOut(BaseModel):
    id: uuid.UUID
    name: str
    timezone: str

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    institute_id: uuid.UUID
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1)


class DepartmentOut(BaseModel):
    id: uuid.UUID
    institute_id: uuid.UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class ProgramCreate(BaseModel):
    department_id: uuid.UUID
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1)
    duration_semesters: int = Field(gt=0)


class ProgramOut(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    code: str
    name: str
    duration_semesters: int

    model_config = {"from_attributes": True}


class BatchCreate(BaseModel):
    program_id: uuid.UUID
    start_year: int
    end_year: int


class BatchOut(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    start_year: int
    end_year: int

    model_config = {"from_attributes": True}


class SemesterCreate(BaseModel):
    batch_id: uuid.UUID
    number: int = Field(gt=0)
    start_date: date
    end_date: date


class SemesterOut(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    number: int
    start_date: date
    end_date: date

    model_config = {"from_attributes": True}


class SectionCreate(BaseModel):
    semester_id: uuid.UUID
    name: str = Field(min_length=1, max_length=20)
    capacity: int = Field(gt=0)


class SectionOut(BaseModel):
    id: uuid.UUID
    semester_id: uuid.UUID
    name: str
    capacity: int

    model_config = {"from_attributes": True}
