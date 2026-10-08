"""FR-ADM-007. AC-003."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.core.errors import ValidationError
from app.core.security import hash_password
from app.models.calendar import SlotType
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service
from app.services import calendar_service as service


def _admin(db_session) -> User:
    user = User(
        email=f"admin-{uuid.uuid4().hex}@example.com",
        full_name="Admin",
        password_hash=hash_password("x"),
        role=UserRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _semester_and_section(db_session, admin):
    institute = academic_service.create_institute(
        db_session, actor=admin, name="Inst", timezone="Asia/Kolkata"
    )
    dept = academic_service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = academic_service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    batch = academic_service.create_batch(
        db_session, actor=admin, program_id=program.id, start_year=2024, end_year=2028
    )
    semester = academic_service.create_semester(
        db_session,
        actor=admin,
        batch_id=batch.id,
        number=1,
        start_date=dt.date(2024, 8, 1),
        end_date=dt.date(2024, 12, 20),
    )
    section = academic_service.create_section(
        db_session, actor=admin, semester_id=semester.id, name="A", capacity=60
    )
    return semester, section, program


def test_create_calendar_windows_must_lie_within_term(db_session):
    admin = _admin(db_session)
    semester, _, _ = _semester_and_section(db_session, admin)
    with pytest.raises(ValidationError):
        service.create_academic_calendar(
            db_session,
            actor=admin,
            semester_id=semester.id,
            holidays=[],
            ia_window=(dt.date(2024, 9, 1), dt.date(2024, 9, 10)),
            practical_window=(dt.date(2024, 10, 1), dt.date(2024, 10, 10)),
            university_exam_window=(dt.date(2025, 1, 1), dt.date(2025, 1, 10)),  # outside term
        )


def test_create_calendar_window_start_before_end(db_session):
    admin = _admin(db_session)
    semester, _, _ = _semester_and_section(db_session, admin)
    with pytest.raises(ValidationError):
        service.create_academic_calendar(
            db_session,
            actor=admin,
            semester_id=semester.id,
            holidays=[],
            ia_window=(dt.date(2024, 9, 10), dt.date(2024, 9, 1)),
            practical_window=(dt.date(2024, 10, 1), dt.date(2024, 10, 10)),
            university_exam_window=(dt.date(2024, 12, 1), dt.date(2024, 12, 10)),
        )


def test_create_calendar_success(db_session):
    admin = _admin(db_session)
    semester, _, _ = _semester_and_section(db_session, admin)
    calendar = service.create_academic_calendar(
        db_session,
        actor=admin,
        semester_id=semester.id,
        holidays=["2024-10-02"],
        ia_window=(dt.date(2024, 9, 1), dt.date(2024, 9, 10)),
        practical_window=(dt.date(2024, 10, 1), dt.date(2024, 10, 10)),
        university_exam_window=(dt.date(2024, 12, 1), dt.date(2024, 12, 10)),
    )
    assert calendar.version == 1


def test_exam_date_outside_window_rejected(db_session):
    admin = _admin(db_session)
    semester, section, program = _semester_and_section(db_session, admin)
    calendar = service.create_academic_calendar(
        db_session,
        actor=admin,
        semester_id=semester.id,
        holidays=[],
        ia_window=(dt.date(2024, 9, 1), dt.date(2024, 9, 10)),
        practical_window=(dt.date(2024, 10, 1), dt.date(2024, 10, 10)),
        university_exam_window=(dt.date(2024, 12, 1), dt.date(2024, 12, 10)),
    )

    from app.models.subject import SubjectType
    from app.services import subject_instance_service, subject_service

    subject = subject_service.create_subject(
        db_session,
        actor=admin,
        program_id=program.id,
        semester_no=1,
        code="CS101",
        name="A",
        credits=4,
        type_=SubjectType.CORE,
        elective_group_id=None,
    )
    instance = subject_instance_service.create_subject_instance(
        db_session, actor=admin, subject_id=subject.id, section_id=section.id
    )

    with pytest.raises(ValidationError):
        service.set_exam_date(
            db_session,
            actor=admin,
            subject_instance_id=instance.id,
            exam_date=dt.date(2024, 9, 5),
            calendar=calendar,
        )

    updated = service.set_exam_date(
        db_session,
        actor=admin,
        subject_instance_id=instance.id,
        exam_date=dt.date(2024, 12, 5),
        calendar=calendar,
    )
    assert updated.exam_at is not None


def test_overlap_rejected(db_session):
    admin = _admin(db_session)
    _, section, _ = _semester_and_section(db_session, admin)
    service.add_timetable_slot(
        db_session,
        actor=admin,
        section_id=section.id,
        subject_instance_id=None,
        day_of_week=0,
        start_time=dt.time(9, 0),
        end_time=dt.time(10, 0),
        type_=SlotType.CLASS,
        effective_from=dt.date(2024, 8, 1),
        effective_to=None,
    )
    with pytest.raises(ValidationError):
        service.add_timetable_slot(
            db_session,
            actor=admin,
            section_id=section.id,
            subject_instance_id=None,
            day_of_week=0,
            start_time=dt.time(9, 30),
            end_time=dt.time(10, 30),
            type_=SlotType.LAB,
            effective_from=dt.date(2024, 8, 1),
            effective_to=None,
        )


def test_non_overlapping_slot_succeeds(db_session):
    admin = _admin(db_session)
    _, section, _ = _semester_and_section(db_session, admin)
    service.add_timetable_slot(
        db_session,
        actor=admin,
        section_id=section.id,
        subject_instance_id=None,
        day_of_week=0,
        start_time=dt.time(9, 0),
        end_time=dt.time(10, 0),
        type_=SlotType.CLASS,
        effective_from=dt.date(2024, 8, 1),
        effective_to=None,
    )
    slot = service.add_timetable_slot(
        db_session,
        actor=admin,
        section_id=section.id,
        subject_instance_id=None,
        day_of_week=0,
        start_time=dt.time(10, 0),
        end_time=dt.time(11, 0),
        type_=SlotType.LAB,
        effective_from=dt.date(2024, 8, 1),
        effective_to=None,
    )
    assert slot.start_time == dt.time(10, 0)


def test_slot_start_must_precede_end(db_session):
    admin = _admin(db_session)
    _, section, _ = _semester_and_section(db_session, admin)
    with pytest.raises(ValidationError):
        service.add_timetable_slot(
            db_session,
            actor=admin,
            section_id=section.id,
            subject_instance_id=None,
            day_of_week=0,
            start_time=dt.time(10, 0),
            end_time=dt.time(9, 0),
            type_=SlotType.CLASS,
            effective_from=dt.date(2024, 8, 1),
            effective_to=None,
        )


def test_create_academic_calendar_writes_audit_log(db_session):
    admin = _admin(db_session)
    semester, _, _ = _semester_and_section(db_session, admin)
    calendar = service.create_academic_calendar(
        db_session,
        actor=admin,
        semester_id=semester.id,
        holidays=[],
        ia_window=(dt.date(2024, 9, 1), dt.date(2024, 9, 10)),
        practical_window=(dt.date(2024, 10, 1), dt.date(2024, 10, 10)),
        university_exam_window=(dt.date(2024, 12, 1), dt.date(2024, 12, 10)),
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "CREATE_ACADEMIC_CALENDAR").all()
    assert len(logs) == 1
    assert logs[0].entity_id == str(calendar.id)


def test_set_exam_date_writes_audit_log(db_session):
    admin = _admin(db_session)
    semester, section, program = _semester_and_section(db_session, admin)
    calendar = service.create_academic_calendar(
        db_session,
        actor=admin,
        semester_id=semester.id,
        holidays=[],
        ia_window=(dt.date(2024, 9, 1), dt.date(2024, 9, 10)),
        practical_window=(dt.date(2024, 10, 1), dt.date(2024, 10, 10)),
        university_exam_window=(dt.date(2024, 12, 1), dt.date(2024, 12, 10)),
    )

    from app.models.subject import SubjectType
    from app.services import subject_instance_service, subject_service

    subject = subject_service.create_subject(
        db_session,
        actor=admin,
        program_id=program.id,
        semester_no=1,
        code="CS101",
        name="A",
        credits=4,
        type_=SubjectType.CORE,
        elective_group_id=None,
    )
    instance = subject_instance_service.create_subject_instance(
        db_session, actor=admin, subject_id=subject.id, section_id=section.id
    )
    updated = service.set_exam_date(
        db_session,
        actor=admin,
        subject_instance_id=instance.id,
        exam_date=dt.date(2024, 12, 5),
        calendar=calendar,
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "SET_EXAM_DATE").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(updated.id)


def test_add_timetable_slot_writes_audit_log(db_session):
    admin = _admin(db_session)
    _, section, _ = _semester_and_section(db_session, admin)
    slot = service.add_timetable_slot(
        db_session,
        actor=admin,
        section_id=section.id,
        subject_instance_id=None,
        day_of_week=0,
        start_time=dt.time(9, 0),
        end_time=dt.time(10, 0),
        type_=SlotType.CLASS,
        effective_from=dt.date(2024, 8, 1),
        effective_to=None,
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "ADD_TIMETABLE_SLOT").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(slot.id)
