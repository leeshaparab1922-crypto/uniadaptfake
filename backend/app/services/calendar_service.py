"""Academic calendar and Section timetable validation. FR-ADM-007.

ADR-0011: every mutation here takes the acting Admin as an explicit `actor`
and writes an `audit_logs` row in the same transaction.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.academic_structure import Semester
from app.models.calendar import AcademicCalendar, SectionTimetableSlot, SlotType
from app.models.subject_instance import SubjectInstance
from app.models.user import User
from app.services import audit


def create_academic_calendar(
    db: Session,
    *,
    actor: User,
    semester_id: uuid.UUID,
    holidays: list[str],
    ia_window: tuple[date, date],
    practical_window: tuple[date, date],
    university_exam_window: tuple[date, date],
) -> AcademicCalendar:
    semester = db.get(Semester, semester_id)
    if semester is None:
        raise NotFoundError("Semester not found.")

    for label, (start, end) in (
        ("IA window", ia_window),
        ("practical window", practical_window),
        ("university exam window", university_exam_window),
    ):
        if start >= end:
            raise ValidationError(f"{label} start must precede end.")
        if start < semester.start_date or end > semester.end_date:
            raise ValidationError(
                f"{label} must lie within the term ({semester.start_date}..{semester.end_date})."
            )

    latest_version = db.scalar(
        select(AcademicCalendar.version)
        .where(AcademicCalendar.semester_id == semester_id)
        .order_by(AcademicCalendar.version.desc())
    )
    version = (latest_version or 0) + 1

    calendar = AcademicCalendar(
        semester_id=semester_id,
        version=version,
        holidays=holidays,
        ia_window_start=ia_window[0],
        ia_window_end=ia_window[1],
        practical_window_start=practical_window[0],
        practical_window_end=practical_window[1],
        university_exam_window_start=university_exam_window[0],
        university_exam_window_end=university_exam_window[1],
    )
    db.add(calendar)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_ACADEMIC_CALENDAR",
        entity_type="AcademicCalendar",
        entity_id=calendar.id,
        after={"semester_id": str(semester_id), "version": version},
    )
    db.commit()
    return calendar


def set_exam_date(
    db: Session,
    *,
    actor: User,
    subject_instance_id: uuid.UUID,
    exam_date: date,
    calendar: AcademicCalendar,
) -> SubjectInstance:
    """Val (FR-ADM-007): exact SubjectInstance exam dates lie in their
    applicable (university exam) window."""
    instance = db.get(SubjectInstance, subject_instance_id)
    if instance is None:
        raise NotFoundError("SubjectInstance not found.")
    if not (calendar.university_exam_window_start <= exam_date <= calendar.university_exam_window_end):
        raise ValidationError("Exam date must lie within the university exam window.")
    before = {"exam_at": instance.exam_at.isoformat() if instance.exam_at else None}
    instance.exam_at = datetime.combine(exam_date, time(9, 0), tzinfo=UTC)
    audit.record(
        db,
        actor=actor,
        action="SET_EXAM_DATE",
        entity_type="SubjectInstance",
        entity_id=instance.id,
        before=before,
        after={"exam_at": instance.exam_at.isoformat()},
    )
    db.commit()
    return instance


def add_timetable_slot(
    db: Session,
    *,
    actor: User,
    section_id: uuid.UUID,
    subject_instance_id: uuid.UUID | None,
    day_of_week: int,
    start_time: time,
    end_time: time,
    type_: SlotType,
    effective_from: date,
    effective_to: date | None,
) -> SectionTimetableSlot:
    """Val (FR-ADM-007): start precedes end; overlapping mandatory events for
    the same Section/day are rejected."""
    if start_time >= end_time:
        raise ValidationError("start_time must precede end_time.")
    if not (0 <= day_of_week <= 6):
        raise ValidationError("day_of_week must be 0..6.")

    existing_slots = db.scalars(
        select(SectionTimetableSlot).where(
            SectionTimetableSlot.section_id == section_id,
            SectionTimetableSlot.day_of_week == day_of_week,
        )
    ).all()
    for slot in existing_slots:
        overlaps_period = not (
            (effective_to is not None and effective_to < slot.effective_from)
            or (slot.effective_to is not None and effective_from > slot.effective_to)
        )
        overlaps_time = start_time < slot.end_time and end_time > slot.start_time
        if overlaps_period and overlaps_time:
            raise ValidationError("Overlapping mandatory timetable slot for this Section/day.")

    slot = SectionTimetableSlot(
        section_id=section_id,
        subject_instance_id=subject_instance_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        type=type_,
        effective_from=effective_from,
        effective_to=effective_to,
    )
    db.add(slot)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="ADD_TIMETABLE_SLOT",
        entity_type="SectionTimetableSlot",
        entity_id=slot.id,
        after={"section_id": str(section_id), "day_of_week": day_of_week, "type": type_.value},
    )
    db.commit()
    return slot
