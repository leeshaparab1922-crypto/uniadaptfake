"""Academic calendar/timetable endpoints. FR-ADM-007."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.core.errors import NotFoundError
from app.models.calendar import AcademicCalendar
from app.models.user import UserRole
from app.schemas.calendar import (
    AcademicCalendarCreate,
    AcademicCalendarOut,
    ExamDateSetRequest,
    TimetableSlotCreate,
    TimetableSlotOut,
)
from app.schemas.subject_instance import SubjectInstanceOut
from app.services import calendar_service

router = APIRouter(
    prefix="/admin/calendar",
    tags=["calendar"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)


@router.post("", response_model=AcademicCalendarOut)
def create_academic_calendar(
    payload: AcademicCalendarCreate, db: DbSession, current_user: CurrentUser
) -> AcademicCalendarOut:
    calendar = calendar_service.create_academic_calendar(
        db,
        actor=current_user,
        semester_id=payload.semester_id,
        holidays=payload.holidays,
        ia_window=(payload.ia_window_start, payload.ia_window_end),
        practical_window=(payload.practical_window_start, payload.practical_window_end),
        university_exam_window=(
            payload.university_exam_window_start,
            payload.university_exam_window_end,
        ),
    )
    return AcademicCalendarOut.model_validate(calendar)


@router.post("/exam-dates", response_model=SubjectInstanceOut)
def set_exam_date(
    payload: ExamDateSetRequest, db: DbSession, current_user: CurrentUser
) -> SubjectInstanceOut:
    calendar = db.get(AcademicCalendar, payload.calendar_id)
    if calendar is None:
        raise NotFoundError("Academic calendar not found.")
    instance = calendar_service.set_exam_date(
        db,
        actor=current_user,
        subject_instance_id=payload.subject_instance_id,
        exam_date=payload.exam_date,
        calendar=calendar,
    )
    return SubjectInstanceOut.model_validate(instance)


@router.post("/timetable-slots", response_model=TimetableSlotOut)
def add_timetable_slot(
    payload: TimetableSlotCreate, db: DbSession, current_user: CurrentUser
) -> TimetableSlotOut:
    slot = calendar_service.add_timetable_slot(
        db,
        actor=current_user,
        section_id=payload.section_id,
        subject_instance_id=payload.subject_instance_id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        type_=payload.type,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    return TimetableSlotOut.model_validate(slot)
