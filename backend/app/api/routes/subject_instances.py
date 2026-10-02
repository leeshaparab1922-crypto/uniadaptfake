"""SubjectInstance + TeacherAssignment/SubjectOwnerAssignment endpoints.
FR-ADM-002, FR-ADM-004."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.models.user import UserRole
from app.schemas.subject_instance import (
    SubjectInstanceCreate,
    SubjectInstanceOut,
    SubjectOwnerOut,
    SubjectOwnerSetRequest,
    TeacherAssignmentCreate,
    TeacherAssignmentOut,
)
from app.services import assignment_service, subject_instance_service

router = APIRouter(
    prefix="/admin/subject-instances",
    tags=["subject-instances"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)


@router.post("", response_model=SubjectInstanceOut)
def create_subject_instance(
    payload: SubjectInstanceCreate, db: DbSession, current_user: CurrentUser
) -> SubjectInstanceOut:
    instance = subject_instance_service.create_subject_instance(
        db, actor=current_user, subject_id=payload.subject_id, section_id=payload.section_id
    )
    return SubjectInstanceOut.model_validate(instance)


@router.post("/{subject_instance_id}/activate", response_model=SubjectInstanceOut)
def activate_subject_instance(
    subject_instance_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> SubjectInstanceOut:
    instance = subject_instance_service.activate_subject_instance(
        db, actor=current_user, subject_instance_id=subject_instance_id
    )
    return SubjectInstanceOut.model_validate(instance)


@router.post("/teacher-assignments", response_model=TeacherAssignmentOut)
def assign_teacher(
    payload: TeacherAssignmentCreate, db: DbSession, current_user: CurrentUser
) -> TeacherAssignmentOut:
    assignment = assignment_service.assign_teacher(
        db,
        actor=current_user,
        teacher_id=payload.teacher_id,
        subject_instance_id=payload.subject_instance_id,
        role=payload.role,
    )
    return TeacherAssignmentOut.model_validate(assignment)


@router.post("/subject-owner", response_model=SubjectOwnerOut)
def set_subject_owner(
    payload: SubjectOwnerSetRequest, db: DbSession, current_user: CurrentUser
) -> SubjectOwnerOut:
    owner = assignment_service.set_subject_owner(
        db,
        actor=current_user,
        subject_id=payload.subject_id,
        owner_teacher_id=payload.owner_teacher_id,
        reason=payload.reason,
    )
    return SubjectOwnerOut.model_validate(owner)
