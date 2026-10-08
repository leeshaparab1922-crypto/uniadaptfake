from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.subject import SubjectType


class ElectiveGroupCreate(BaseModel):
    program_id: uuid.UUID
    semester_no: int = Field(gt=0)
    name: str = Field(min_length=1)
    required: bool = True


class ElectiveGroupOut(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    semester_no: int
    name: str
    required: bool

    model_config = {"from_attributes": True}


class SubjectCreate(BaseModel):
    program_id: uuid.UUID
    semester_no: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1)
    credits: int = Field(ge=0)
    type: SubjectType
    elective_group_id: uuid.UUID | None = None


class SubjectOut(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    semester_no: int
    code: str
    name: str
    credits: int
    type: SubjectType
    elective_group_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class UnitIn(BaseModel):
    order_index: int = Field(ge=0)
    name: str = Field(min_length=1)
    weightage: int = Field(ge=0, le=100)


class UnitsSetRequest(BaseModel):
    units: list[UnitIn] = Field(min_length=1)


class UnitOut(BaseModel):
    id: uuid.UUID
    order_index: int
    name: str
    weightage: int

    model_config = {"from_attributes": True}
