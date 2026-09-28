"""SubjectInstance mapping + activation gate. FR-ADM-004.

New test file added per Rework 2 (verification-report.md's Re-verification
(2026-09-28) Finding B / Blocking Issue 2): asserts an `audit_logs` row for
both `create_subject_instance` and `activate_subject_instance`, and covers
this service's own two previously-untested validation branches (Program/
Semester mismatch at subject_instance_service.py:39, duplicate instance at
subject_instance_service.py:48).
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.core.errors import NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.subject import SubjectType
from app.models.subject_instance import SubjectInstanceStatus, TeacherAssignmentRole
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service
from app.services import assignment_service, subject_service
from app.services import subject_instance_service as service


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


def _program_and_section(db_session, admin, *, semester_no=1):
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
        number=semester_no,
        start_date=dt.date(2024, 8, 1),
        end_date=dt.date(2024, 12, 1),
    )
    section = academic_service.create_section(
        db_session, actor=admin, semester_id=semester.id, name="A", capacity=60
    )
    return program, semester, section


def _subject(db_session, admin, program, *, semester_no=1, code="CS101"):
    return subject_service.create_subject(
        db_session,
        actor=admin,
        program_id=program.id,
        semester_no=semester_no,
        code=code,
        name="A",
        credits=4,
        type_=SubjectType.CORE,
        elective_group_id=None,
    )


def test_create_subject_instance_writes_audit_log(db_session):
    admin = _admin(db_session)
    program, _, section = _program_and_section(db_session, admin)
    subject = _subject(db_session, admin, program)

    instance = service.create_subject_instance(
        db_session, actor=admin, subject_id=subject.id, section_id=section.id
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "CREATE_SUBJECT_INSTANCE").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(instance.id)
    assert instance.status == SubjectInstanceStatus.DRAFT


def test_create_subject_instance_program_semester_mismatch_rejected(db_session):
    """FR-ADM-004 Val: Subject's Program/Semester must match the Section's
    Program/Semester path (subject_instance_service.py:39)."""
    admin = _admin(db_session)
    program, _, section = _program_and_section(db_session, admin, semester_no=1)
    # Subject declared for semester 2, but the Section's path is semester 1.
    subject = _subject(db_session, admin, program, semester_no=2)

    with pytest.raises(ValidationError):
        service.create_subject_instance(db_session, actor=admin, subject_id=subject.id, section_id=section.id)


def test_create_subject_instance_duplicate_rejected(db_session):
    """subject_instance_service.py:48 - a second SubjectInstance for the same
    Subject/Section pair is rejected."""
    admin = _admin(db_session)
    program, _, section = _program_and_section(db_session, admin)
    subject = _subject(db_session, admin, program)
    service.create_subject_instance(db_session, actor=admin, subject_id=subject.id, section_id=section.id)

    with pytest.raises(ValidationError):
        service.create_subject_instance(db_session, actor=admin, subject_id=subject.id, section_id=section.id)


def test_create_subject_instance_unknown_subject_not_found(db_session):
    admin = _admin(db_session)
    _, _, section = _program_and_section(db_session, admin)
    with pytest.raises(NotFoundError):
        service.create_subject_instance(
            db_session, actor=admin, subject_id=uuid.uuid4(), section_id=section.id
        )


def test_create_subject_instance_unknown_section_not_found(db_session):
    admin = _admin(db_session)
    program, _, _ = _program_and_section(db_session, admin)
    subject = _subject(db_session, admin, program)
    with pytest.raises(NotFoundError):
        service.create_subject_instance(
            db_session, actor=admin, subject_id=subject.id, section_id=uuid.uuid4()
        )


def test_activate_subject_instance_requires_teacher_rejected(db_session):
    admin = _admin(db_session)
    program, _, section = _program_and_section(db_session, admin)
    subject = _subject(db_session, admin, program)
    instance = service.create_subject_instance(
        db_session, actor=admin, subject_id=subject.id, section_id=section.id
    )
    with pytest.raises(ValidationError):
        service.activate_subject_instance(db_session, actor=admin, subject_instance_id=instance.id)


def test_activate_subject_instance_unknown_instance_not_found(db_session):
    admin = _admin(db_session)
    with pytest.raises(NotFoundError):
        service.activate_subject_instance(db_session, actor=admin, subject_instance_id=uuid.uuid4())


def test_activate_subject_instance_writes_audit_log(db_session):
    admin = _admin(db_session)
    program, _, section = _program_and_section(db_session, admin)
    subject = _subject(db_session, admin, program)
    instance = service.create_subject_instance(
        db_session, actor=admin, subject_id=subject.id, section_id=section.id
    )
    teacher = User(
        email="teacher@example.com",
        full_name="T",
        password_hash=hash_password("x"),
        role=UserRole.TEACHER,
        is_active=True,
        token_version=0,
    )
    db_session.add(teacher)
    db_session.commit()
    assignment_service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )

    activated = service.activate_subject_instance(db_session, actor=admin, subject_instance_id=instance.id)
    assert activated.status == SubjectInstanceStatus.ACTIVE

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "ACTIVATE_SUBJECT_INSTANCE").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(instance.id)
