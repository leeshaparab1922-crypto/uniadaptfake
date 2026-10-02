"""FR-ADM-002. ADR-0003: exactly one owner per Subject."""

from __future__ import annotations

import datetime as dt

import pytest

from app.core.errors import ValidationError
from app.core.security import hash_password
from app.models.subject import SubjectType
from app.models.subject_instance import TeacherAssignmentRole
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service
from app.services import assignment_service as service
from app.services import subject_instance_service, subject_service


def _teacher(db_session, email="teacher@example.com") -> User:
    user = User(
        email=email,
        full_name="Teacher",
        password_hash=hash_password("x"),
        role=UserRole.TEACHER,
        is_active=True,
        token_version=0,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _admin(db_session) -> User:
    import uuid

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


def _instance(db_session, admin):
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
        end_date=dt.date(2024, 12, 1),
    )
    section = academic_service.create_section(
        db_session, actor=admin, semester_id=semester.id, name="A", capacity=60
    )
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
    return subject, instance


def test_assign_teacher_requires_teacher_role(db_session):
    admin = _admin(db_session)
    _, instance = _instance(db_session, admin)
    non_teacher = _admin(db_session)
    with pytest.raises(ValidationError):
        service.assign_teacher(
            db_session,
            actor=admin,
            teacher_id=non_teacher.id,
            subject_instance_id=instance.id,
            role=TeacherAssignmentRole.PRIMARY,
        )


def test_assign_teacher_success(db_session):
    admin = _admin(db_session)
    _, instance = _instance(db_session, admin)
    teacher = _teacher(db_session)
    assignment = service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )
    assert assignment.role == TeacherAssignmentRole.PRIMARY


def test_active_instance_requires_teacher(db_session):
    admin = _admin(db_session)
    _, instance = _instance(db_session, admin)
    with pytest.raises(ValidationError):
        subject_instance_service.activate_subject_instance(
            db_session, actor=admin, subject_instance_id=instance.id
        )


def test_activation_succeeds_after_teacher_assigned(db_session):
    admin = _admin(db_session)
    _, instance = _instance(db_session, admin)
    teacher = _teacher(db_session)
    service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )
    activated = subject_instance_service.activate_subject_instance(
        db_session, actor=admin, subject_instance_id=instance.id
    )
    assert activated.status.value == "ACTIVE"


def test_set_subject_owner_requires_primary_assignment(db_session):
    admin = _admin(db_session)
    subject, instance = _instance(db_session, admin)
    teacher = _teacher(db_session)
    with pytest.raises(ValidationError):
        service.set_subject_owner(db_session, actor=admin, subject_id=subject.id, owner_teacher_id=teacher.id)


def test_exactly_one_owner_enforced(db_session):
    admin = _admin(db_session)
    subject, instance = _instance(db_session, admin)
    teacher1 = _teacher(db_session, email="t1@example.com")
    teacher2 = _teacher(db_session, email="t2@example.com")
    service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher1.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )
    service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher2.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )
    owner = service.set_subject_owner(
        db_session, actor=admin, subject_id=subject.id, owner_teacher_id=teacher1.id
    )
    assert owner.owner_teacher_id == teacher1.id

    # Re-assigning to teacher2 updates the same row in place (unique index on subject_id).
    owner2 = service.set_subject_owner(
        db_session, actor=admin, subject_id=subject.id, owner_teacher_id=teacher2.id
    )
    assert owner2.id == owner.id
    assert owner2.owner_teacher_id == teacher2.id

    from app.models.subject_instance import SubjectOwnerAssignment

    all_owners = (
        db_session.query(SubjectOwnerAssignment).filter(SubjectOwnerAssignment.subject_id == subject.id).all()
    )
    assert len(all_owners) == 1


def test_set_subject_owner_writes_audit_log(db_session):
    admin = _admin(db_session)
    subject, instance = _instance(db_session, admin)
    teacher = _teacher(db_session)
    service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )
    service.set_subject_owner(
        db_session, actor=admin, subject_id=subject.id, owner_teacher_id=teacher.id, reason="init"
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "SET_SUBJECT_OWNER").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id


def test_assign_teacher_writes_audit_log(db_session):
    admin = _admin(db_session)
    _, instance = _instance(db_session, admin)
    teacher = _teacher(db_session)
    service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "ASSIGN_TEACHER").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id


def test_active_instances_missing_teacher(db_session):
    admin = _admin(db_session)
    subject, instance = _instance(db_session, admin)
    teacher = _teacher(db_session)
    service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )
    subject_instance_service.activate_subject_instance(
        db_session, actor=admin, subject_instance_id=instance.id
    )
    missing = service.active_instances_missing_teacher(db_session)
    assert instance.id not in [i.id for i in missing]
