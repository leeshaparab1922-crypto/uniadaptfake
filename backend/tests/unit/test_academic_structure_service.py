"""FR-ADM-001. AC: a Section cannot be created without a valid semester/batch path."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.core.errors import NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services import academic_structure_service as service


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


def _institute(db_session, admin):
    return service.create_institute(db_session, actor=admin, name="Test Institute", timezone="Asia/Kolkata")


def _full_path(db_session, admin):
    institute = _institute(db_session, admin)
    dept = service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    batch = service.create_batch(
        db_session, actor=admin, program_id=program.id, start_year=2024, end_year=2028
    )
    semester = service.create_semester(
        db_session,
        actor=admin,
        batch_id=batch.id,
        number=1,
        start_date=dt.date(2024, 8, 1),
        end_date=dt.date(2024, 12, 1),
    )
    return institute, dept, program, batch, semester


def test_create_section_requires_valid_semester(db_session):
    admin = _admin(db_session)
    with pytest.raises(NotFoundError):
        service.create_section(db_session, actor=admin, semester_id=uuid.uuid4(), name="A", capacity=60)


def test_create_section_success(db_session):
    admin = _admin(db_session)
    *_, semester = _full_path(db_session, admin)
    section = service.create_section(db_session, actor=admin, semester_id=semester.id, name="A", capacity=60)
    assert section.capacity == 60


def test_create_section_nonpositive_capacity_rejected(db_session):
    admin = _admin(db_session)
    *_, semester = _full_path(db_session, admin)
    with pytest.raises(ValidationError):
        service.create_section(db_session, actor=admin, semester_id=semester.id, name="A", capacity=0)


def test_duplicate_department_code_rejected(db_session):
    admin = _admin(db_session)
    institute = _institute(db_session, admin)
    service.create_department(db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE")
    with pytest.raises(ValidationError):
        service.create_department(
            db_session, actor=admin, institute_id=institute.id, code="cse", name="Duplicate"
        )


def test_semester_start_must_precede_end(db_session):
    admin = _admin(db_session)
    institute = _institute(db_session, admin)
    dept = service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    batch = service.create_batch(
        db_session, actor=admin, program_id=program.id, start_year=2024, end_year=2028
    )
    with pytest.raises(ValidationError):
        service.create_semester(
            db_session,
            actor=admin,
            batch_id=batch.id,
            number=1,
            start_date=dt.date(2024, 12, 1),
            end_date=dt.date(2024, 8, 1),
        )


def test_batch_start_year_after_end_year_rejected(db_session):
    admin = _admin(db_session)
    institute = _institute(db_session, admin)
    dept = service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    with pytest.raises(ValidationError):
        service.create_batch(db_session, actor=admin, program_id=program.id, start_year=2028, end_year=2024)


def test_duplicate_section_name_per_semester_rejected(db_session):
    admin = _admin(db_session)
    *_, semester = _full_path(db_session, admin)
    service.create_section(db_session, actor=admin, semester_id=semester.id, name="A", capacity=60)
    with pytest.raises(ValidationError):
        service.create_section(db_session, actor=admin, semester_id=semester.id, name="A", capacity=30)


def test_create_institute_writes_audit_log(db_session):
    admin = _admin(db_session)
    institute = _institute(db_session, admin)

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "CREATE_INSTITUTE").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(institute.id)


def _audit_logs(db_session, action: str):
    from app.models.audit_log import AuditLog

    return db_session.query(AuditLog).filter(AuditLog.action == action).all()


def test_create_department_writes_audit_log(db_session):
    admin = _admin(db_session)
    institute = _institute(db_session, admin)
    dept = service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    logs = _audit_logs(db_session, "CREATE_DEPARTMENT")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(dept.id)


def test_create_program_writes_audit_log(db_session):
    admin = _admin(db_session)
    institute = _institute(db_session, admin)
    dept = service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    logs = _audit_logs(db_session, "CREATE_PROGRAM")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(program.id)


def test_create_batch_writes_audit_log(db_session):
    admin = _admin(db_session)
    institute = _institute(db_session, admin)
    dept = service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    batch = service.create_batch(
        db_session, actor=admin, program_id=program.id, start_year=2024, end_year=2028
    )
    logs = _audit_logs(db_session, "CREATE_BATCH")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(batch.id)


def test_create_semester_writes_audit_log(db_session):
    admin = _admin(db_session)
    institute = _institute(db_session, admin)
    dept = service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    batch = service.create_batch(
        db_session, actor=admin, program_id=program.id, start_year=2024, end_year=2028
    )
    semester = service.create_semester(
        db_session,
        actor=admin,
        batch_id=batch.id,
        number=1,
        start_date=dt.date(2024, 8, 1),
        end_date=dt.date(2024, 12, 1),
    )
    logs = _audit_logs(db_session, "CREATE_SEMESTER")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(semester.id)


def test_create_section_writes_audit_log(db_session):
    admin = _admin(db_session)
    *_, semester = _full_path(db_session, admin)
    section = service.create_section(db_session, actor=admin, semester_id=semester.id, name="A", capacity=60)
    logs = _audit_logs(db_session, "CREATE_SECTION")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(section.id)
