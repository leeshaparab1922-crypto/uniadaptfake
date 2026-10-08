"""Teacher-facing, Section-scoped reads. FR-AUTH-002, AC-001.

AC-001: "GIVEN a Teacher assigned to Section A WHEN requesting its Students
THEN only Section A records return. NEGATIVE: GIVEN the same Teacher
requests Section B WHEN unassigned THEN 403/404 returns with no data."

The authorization check (does this Teacher hold any TeacherAssignment on a
SubjectInstance of this Section?) and the data read are both separate,
query-level DB filters - never fetch-then-filter in Python - matching the
same pattern `enrollments.py::my_enrollments` already uses for Students
(NFR-SEC-006/007/008).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.student import Student
from app.models.subject_instance import SubjectInstance, TeacherAssignment
from app.models.user import User


def _teacher_has_section_access(db: Session, *, teacher_id: uuid.UUID, section_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(TeacherAssignment.id)
            .join(SubjectInstance, SubjectInstance.id == TeacherAssignment.subject_instance_id)
            .where(
                TeacherAssignment.teacher_id == teacher_id,
                SubjectInstance.section_id == section_id,
            )
        )
        is not None
    )


def list_students_for_section(db: Session, *, teacher: User, section_id: uuid.UUID) -> list[Student]:
    """Returns Students in `section_id` only if `teacher` holds a
    TeacherAssignment on a SubjectInstance of that Section. An unassigned
    Section raises `NotFoundError` (mapped to 404) - no row data is
    returned or distinguishable from "Section does not exist"."""
    if not _teacher_has_section_access(db, teacher_id=teacher.id, section_id=section_id):
        raise NotFoundError("Section not found, or not assigned to this Teacher.")
    return list(db.scalars(select(Student).where(Student.section_id == section_id)).all())
