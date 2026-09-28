"""Subject/Unit/ElectiveGroup endpoints. FR-ADM-003."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.models.user import UserRole
from app.schemas.subject import (
    ElectiveGroupCreate,
    ElectiveGroupOut,
    SubjectCreate,
    SubjectOut,
    UnitOut,
    UnitsSetRequest,
)
from app.services import subject_service as service

router = APIRouter(
    prefix="/admin/subjects",
    tags=["subjects"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)


@router.post("/elective-groups", response_model=ElectiveGroupOut)
def create_elective_group(
    payload: ElectiveGroupCreate, db: DbSession, current_user: CurrentUser
) -> ElectiveGroupOut:
    group = service.create_elective_group(
        db,
        actor=current_user,
        program_id=payload.program_id,
        semester_no=payload.semester_no,
        name=payload.name,
        required=payload.required,
    )
    return ElectiveGroupOut.model_validate(group)


@router.post("", response_model=SubjectOut)
def create_subject(payload: SubjectCreate, db: DbSession, current_user: CurrentUser) -> SubjectOut:
    subject = service.create_subject(
        db,
        actor=current_user,
        program_id=payload.program_id,
        semester_no=payload.semester_no,
        code=payload.code,
        name=payload.name,
        credits=payload.credits,
        type_=payload.type,
        elective_group_id=payload.elective_group_id,
    )
    return SubjectOut.model_validate(subject)


@router.put("/{subject_id}/units", response_model=list[UnitOut])
def set_units(
    subject_id: uuid.UUID, payload: UnitsSetRequest, db: DbSession, current_user: CurrentUser
) -> list[UnitOut]:
    units = service.set_units(
        db, actor=current_user, subject_id=subject_id, units=[u.model_dump() for u in payload.units]
    )
    return [UnitOut.model_validate(u) for u in units]
