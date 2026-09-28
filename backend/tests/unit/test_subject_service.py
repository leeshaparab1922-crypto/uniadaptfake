"""FR-ADM-003. ADR-0002: Unit weight sum-to-100 under a Subject row lock."""

from __future__ import annotations

import uuid

import pytest

from app.core.errors import NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.subject import SubjectType
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service
from app.services import subject_service as service


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


def _program(db_session, admin):
    institute = academic_service.create_institute(
        db_session, actor=admin, name="Inst", timezone="Asia/Kolkata"
    )
    dept = academic_service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    return academic_service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )


def test_create_subject_duplicate_code_rejected(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    service.create_subject(
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
    with pytest.raises(ValidationError):
        service.create_subject(
            db_session,
            actor=admin,
            program_id=program.id,
            semester_no=1,
            code="cs101",
            name="B",
            credits=3,
            type_=SubjectType.CORE,
            elective_group_id=None,
        )


def test_create_subject_invalid_scope_rejected(db_session):
    admin = _admin(db_session)
    with pytest.raises(NotFoundError):
        service.create_subject(
            db_session,
            actor=admin,
            program_id=uuid.uuid4(),
            semester_no=1,
            code="CS101",
            name="A",
            credits=4,
            type_=SubjectType.CORE,
            elective_group_id=None,
        )


def test_elective_subject_requires_group(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    with pytest.raises(ValidationError):
        service.create_subject(
            db_session,
            actor=admin,
            program_id=program.id,
            semester_no=1,
            code="OE1",
            name="Elective",
            credits=3,
            type_=SubjectType.ELECTIVE,
            elective_group_id=None,
        )


def test_core_subject_cannot_have_elective_group(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    group = service.create_elective_group(
        db_session, actor=admin, program_id=program.id, semester_no=1, name="G1", required=True
    )
    with pytest.raises(ValidationError):
        service.create_subject(
            db_session,
            actor=admin,
            program_id=program.id,
            semester_no=1,
            code="CS101",
            name="Core",
            credits=4,
            type_=SubjectType.CORE,
            elective_group_id=group.id,
        )


def test_set_units_sum_exactly_100_succeeds(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    subject = service.create_subject(
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
    units = service.set_units(
        db_session,
        actor=admin,
        subject_id=subject.id,
        units=[
            {"order_index": 1, "name": "U1", "weightage": 50},
            {"order_index": 2, "name": "U2", "weightage": 50},
        ],
    )
    assert sum(u.weightage for u in units) == 100


def test_set_units_sum_below_100_rejected(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    subject = service.create_subject(
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
    with pytest.raises(ValidationError):
        service.set_units(
            db_session,
            actor=admin,
            subject_id=subject.id,
            units=[
                {"order_index": 1, "name": "U1", "weightage": 40},
                {"order_index": 2, "name": "U2", "weightage": 50},
            ],
        )


def test_set_units_sum_above_100_rejected(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    subject = service.create_subject(
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
    with pytest.raises(ValidationError):
        service.set_units(
            db_session,
            actor=admin,
            subject_id=subject.id,
            units=[
                {"order_index": 1, "name": "U1", "weightage": 60},
                {"order_index": 2, "name": "U2", "weightage": 60},
            ],
        )


def test_set_units_out_of_range_weight_rejected(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    subject = service.create_subject(
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
    with pytest.raises(ValidationError):
        service.set_units(
            db_session,
            actor=admin,
            subject_id=subject.id,
            units=[{"order_index": 1, "name": "U1", "weightage": 150}],
        )


def test_set_units_replace_is_atomic_on_failure(db_session):
    """A failed re-set (bad sum) must not clobber the previously valid Units."""
    admin = _admin(db_session)
    program = _program(db_session, admin)
    subject = service.create_subject(
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
    service.set_units(
        db_session,
        actor=admin,
        subject_id=subject.id,
        units=[{"order_index": 1, "name": "U1", "weightage": 100}],
    )
    with pytest.raises(ValidationError):
        service.set_units(
            db_session,
            actor=admin,
            subject_id=subject.id,
            units=[{"order_index": 1, "name": "U1-bad", "weightage": 50}],
        )
    db_session.rollback()
    from app.models.subject import Unit

    remaining = db_session.query(Unit).filter(Unit.subject_id == subject.id).all()
    assert len(remaining) == 1
    assert remaining[0].weightage == 100


def test_create_subject_writes_audit_log(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    subject = service.create_subject(
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

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "CREATE_SUBJECT").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(subject.id)


def test_create_elective_group_writes_audit_log(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    group = service.create_elective_group(
        db_session, actor=admin, program_id=program.id, semester_no=1, name="G1", required=True
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "CREATE_ELECTIVE_GROUP").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(group.id)


def test_set_units_writes_audit_log(db_session):
    admin = _admin(db_session)
    program = _program(db_session, admin)
    subject = service.create_subject(
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
    service.set_units(
        db_session,
        actor=admin,
        subject_id=subject.id,
        units=[{"order_index": 1, "name": "U1", "weightage": 100}],
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "SET_UNITS").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(subject.id)
