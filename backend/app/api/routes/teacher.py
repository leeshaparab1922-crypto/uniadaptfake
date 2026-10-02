"""Teacher-facing, Section-scoped reads. FR-AUTH-002, AC-001."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require_role
from app.models.user import UserRole
from app.schemas.student import StudentOut
from app.services import teacher_service

router = APIRouter(
    prefix="/teacher",
    tags=["teacher"],
    dependencies=[Depends(require_role(UserRole.TEACHER))],
)


@router.get("/sections/{section_id}/students", response_model=list[StudentOut])
def list_section_students(
    section_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> list[StudentOut]:
    """AC-001: only Students of a Section where the caller holds a
    TeacherAssignment are returned; an unassigned Section is a 404 with no
    data (NFR-SEC-006/007/008 - scoped at the query level)."""
    students = teacher_service.list_students_for_section(db, teacher=current_user, section_id=section_id)
    return [StudentOut.model_validate(s) for s in students]
