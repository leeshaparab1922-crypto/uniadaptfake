"""Read-only Student enrollment list (FR-STU-001) and Admin
allocation/promotion/transfer preview+confirm endpoints (FR-ADM-006).

BUS-001: no mutation route exists here for a Student caller - the Student
endpoints below (`/enrollments/me`) are GET-only, and every mutating route
in this file requires `require_role(UserRole.ADMIN)`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.core.errors import NotFoundError, ValidationError
from app.models.student import Student
from app.models.user import UserRole
from app.schemas.enrollment import (
    AssignElectiveRequest,
    EnrollmentOut,
    PromotionConfirmResponse,
    PromotionPreviewItemOut,
    PromotionPreviewResponse,
    PromotionRequest,
)
from app.services import enrollment_service

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


def _student_for_user(db: DbSession, user_id: uuid.UUID) -> Student:
    from sqlalchemy import select

    student = db.scalar(select(Student).where(Student.user_id == user_id))
    if student is None:
        raise NotFoundError("No Student record for this account.")
    return student


@router.get("/me", response_model=list[EnrollmentOut])
def my_enrollments(db: DbSession, current_user: CurrentUser) -> list[EnrollmentOut]:
    """FR-STU-001: read-only. Scoped to the caller's own Student record
    (NFR-SEC-006/007/008) - there is deliberately no request parameter that
    lets a Student read another Student's enrollments."""
    if current_user.role != UserRole.STUDENT:
        raise ValidationError("Only Student accounts have an enrollment list.")
    student = _student_for_user(db, current_user.id)
    enrollments = enrollment_service.get_active_enrollments(db, student_id=student.id)
    return [EnrollmentOut.model_validate(e) for e in enrollments]


admin_router = APIRouter(
    prefix="/admin/enrollments",
    tags=["enrollments-admin"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)


@admin_router.post("/auto-enroll/{student_id}", response_model=list[EnrollmentOut])
def auto_enroll(student_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> list[EnrollmentOut]:
    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Student not found.")
    created = enrollment_service.auto_enroll_student(db, actor=current_user, student=student)
    return [EnrollmentOut.model_validate(e) for e in created]


@admin_router.post("/electives", response_model=EnrollmentOut)
def assign_elective(
    payload: AssignElectiveRequest, db: DbSession, current_user: CurrentUser
) -> EnrollmentOut:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise NotFoundError("Student not found.")
    enrollment = enrollment_service.assign_elective(
        db,
        actor=current_user,
        student=student,
        elective_group_id=payload.elective_group_id,
        subject_id=payload.subject_id,
    )
    return EnrollmentOut.model_validate(enrollment)


@admin_router.post("/promotion/preview", response_model=PromotionPreviewResponse)
def preview_promotion(payload: PromotionRequest, db: DbSession) -> PromotionPreviewResponse:
    preview = enrollment_service.preview_promotion(
        db,
        student_ids=payload.student_ids,
        to_batch_id=payload.to_batch_id,
        to_semester_no=payload.to_semester_no,
        to_section_id=payload.to_section_id,
    )
    return PromotionPreviewResponse(
        items=[
            PromotionPreviewItemOut(
                student_id=i.student_id,
                roll_number=i.roll_number,
                from_section_id=i.from_section_id,
                to_section_id=i.to_section_id,
                capacity_conflict=i.capacity_conflict,
            )
            for i in preview.items
        ],
        has_conflicts=preview.has_conflicts,
    )


@admin_router.post("/promotion/confirm", response_model=PromotionConfirmResponse)
def confirm_promotion(
    payload: PromotionRequest, db: DbSession, current_user: CurrentUser
) -> PromotionConfirmResponse:
    operation_id = enrollment_service.confirm_promotion(
        db,
        actor=current_user,
        student_ids=payload.student_ids,
        to_batch_id=payload.to_batch_id,
        to_semester_no=payload.to_semester_no,
        to_section_id=payload.to_section_id,
    )
    return PromotionConfirmResponse(operation_id=operation_id)
