"""FR-ADM-006. BUS-001, BUS-002, BUS-049. AC-002, AC-030."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.enrollment import EnrollmentStatus
from app.models.student import Student
from app.models.subject import SubjectType
from app.models.subject_instance import TeacherAssignmentRole
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service
from app.services import assignment_service, enrollment_service, subject_instance_service, subject_service


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


def _setup(db_session, *, section_capacity=2):
    admin = _admin(db_session)
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
        db_session, actor=admin, semester_id=semester.id, name="A", capacity=section_capacity
    )

    core_subject = subject_service.create_subject(
        db_session,
        actor=admin,
        program_id=program.id,
        semester_no=1,
        code="CS101",
        name="Core",
        credits=4,
        type_=SubjectType.CORE,
        elective_group_id=None,
    )
    group = subject_service.create_elective_group(
        db_session, actor=admin, program_id=program.id, semester_no=1, name="OE", required=True
    )
    elective_subject = subject_service.create_subject(
        db_session,
        actor=admin,
        program_id=program.id,
        semester_no=1,
        code="OE101",
        name="Elective",
        credits=3,
        type_=SubjectType.ELECTIVE,
        elective_group_id=group.id,
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

    core_instance = subject_instance_service.create_subject_instance(
        db_session, actor=admin, subject_id=core_subject.id, section_id=section.id
    )
    elective_instance = subject_instance_service.create_subject_instance(
        db_session, actor=admin, subject_id=elective_subject.id, section_id=section.id
    )
    for instance in (core_instance, elective_instance):
        assignment_service.assign_teacher(
            db_session,
            actor=admin,
            teacher_id=teacher.id,
            subject_instance_id=instance.id,
            role=TeacherAssignmentRole.PRIMARY,
        )
        subject_instance_service.activate_subject_instance(
            db_session, actor=admin, subject_instance_id=instance.id
        )

    return {
        "admin": admin,
        "program": program,
        "batch": batch,
        "semester": semester,
        "section": section,
        "core_subject": core_subject,
        "elective_subject": elective_subject,
        "elective_group": group,
    }


def _make_student(db_session, ctx, *, roll="R1", email="student@example.com") -> Student:
    user = User(
        email=email,
        full_name="S",
        password_hash=hash_password("x"),
        role=UserRole.STUDENT,
        is_active=True,
        token_version=0,
    )
    db_session.add(user)
    db_session.flush()
    student = Student(
        user_id=user.id,
        roll_number=roll,
        department_id=ctx["program"].department_id,
        batch_id=ctx["batch"].id,
        section_id=ctx["section"].id,
        current_semester_no=1,
    )
    db_session.add(student)
    db_session.commit()
    return student


def _promotion_target(db_session, ctx, *, number=2, capacity=5, name="B"):
    """A Semester/Section pair under the *same* batch as `ctx`, consistent
    with `to_batch_id`/`to_semester_no` (FR-ADM-006 Val "no ... mismatches")."""
    semester = academic_service.create_semester(
        db_session,
        actor=ctx["admin"],
        batch_id=ctx["batch"].id,
        number=number,
        start_date=dt.date(2025, 1, 1),
        end_date=dt.date(2025, 5, 1),
    )
    section = academic_service.create_section(
        db_session, actor=ctx["admin"], semester_id=semester.id, name=name, capacity=capacity
    )
    return semester, section


def _counts(db_session):
    from app.models.audit_log import AuditLog
    from app.models.enrollment import Enrollment, StudentPlacementHistory

    return (
        db_session.query(Enrollment).count(),
        db_session.query(StudentPlacementHistory).count(),
        db_session.query(AuditLog).count(),
    )


def test_auto_enroll_creates_core_only_not_elective(db_session):
    ctx = _setup(db_session)
    student = _make_student(db_session, ctx)
    created = enrollment_service.auto_enroll_student(db_session, actor=ctx["admin"], student=student)
    assert len(created) == 1
    assert created[0].subject_instance_id != ctx["elective_subject"].id


def test_auto_enroll_idempotent(db_session):
    ctx = _setup(db_session)
    student = _make_student(db_session, ctx)
    enrollment_service.auto_enroll_student(db_session, actor=ctx["admin"], student=student)
    second = enrollment_service.auto_enroll_student(db_session, actor=ctx["admin"], student=student)
    assert second == []
    active = enrollment_service.get_active_enrollments(db_session, student_id=student.id)
    assert len(active) == 1


def test_single_elective_per_group(db_session):
    ctx = _setup(db_session)
    student = _make_student(db_session, ctx)
    enrollment_service.assign_elective(
        db_session,
        actor=ctx["admin"],
        student=student,
        elective_group_id=ctx["elective_group"].id,
        subject_id=ctx["elective_subject"].id,
    )
    active = enrollment_service.get_active_enrollments(db_session, student_id=student.id)
    elective_enrollments = [e for e in active if e.elective_group_id == ctx["elective_group"].id]
    assert len(elective_enrollments) == 1


def test_missing_required_elective_rejected(db_session):
    ctx = _setup(db_session)
    student = _make_student(db_session, ctx)
    missing = enrollment_service.required_electives_missing(db_session, student=student)
    assert ctx["elective_group"].id in [g.id for g in missing]


def test_elective_capacity_overflow_rejected(db_session):
    ctx = _setup(db_session, section_capacity=1)
    student1 = _make_student(db_session, ctx, roll="R1", email="s1@example.com")
    student2 = _make_student(db_session, ctx, roll="R2", email="s2@example.com")
    enrollment_service.assign_elective(
        db_session,
        actor=ctx["admin"],
        student=student1,
        elective_group_id=ctx["elective_group"].id,
        subject_id=ctx["elective_subject"].id,
    )
    with pytest.raises(ConflictError):
        enrollment_service.assign_elective(
            db_session,
            actor=ctx["admin"],
            student=student2,
            elective_group_id=ctx["elective_group"].id,
            subject_id=ctx["elective_subject"].id,
        )


def test_student_enrollment_list_is_read_only_at_service_level(db_session):
    """Sanity: `get_active_enrollments` has no side effects."""
    ctx = _setup(db_session)
    student = _make_student(db_session, ctx)
    enrollment_service.auto_enroll_student(db_session, actor=ctx["admin"], student=student)
    before = enrollment_service.get_active_enrollments(db_session, student_id=student.id)
    after = enrollment_service.get_active_enrollments(db_session, student_id=student.id)
    assert len(before) == len(after)


def test_promotion_preview_no_mutation(db_session):
    ctx = _setup(db_session, section_capacity=5)
    student = _make_student(db_session, ctx)
    original_section_id = student.section_id
    target_semester, target_section = _promotion_target(db_session, ctx)
    preview = enrollment_service.preview_promotion(
        db_session,
        student_ids=[student.id],
        to_batch_id=ctx["batch"].id,
        to_semester_no=target_semester.number,
        to_section_id=target_section.id,
    )
    assert preview.has_conflicts is False
    db_session.refresh(student)
    assert student.section_id == original_section_id  # unchanged - preview is read-only


def test_promotion_confirm_atomic_with_history(db_session):
    ctx = _setup(db_session, section_capacity=5)
    student = _make_student(db_session, ctx)
    enrollment_service.auto_enroll_student(db_session, actor=ctx["admin"], student=student)
    target_semester, target_section = _promotion_target(db_session, ctx)

    operation_id = enrollment_service.confirm_promotion(
        db_session,
        actor=ctx["admin"],
        student_ids=[student.id],
        to_batch_id=ctx["batch"].id,
        to_semester_no=target_semester.number,
        to_section_id=target_section.id,
    )
    assert operation_id is not None

    from app.models.enrollment import StudentPlacementHistory

    history = (
        db_session.query(StudentPlacementHistory)
        .filter(StudentPlacementHistory.student_id == student.id)
        .all()
    )
    assert len(history) == 1
    assert history[0].to_semester_no == target_semester.number

    # Prior active enrollment is CLOSED (history preserved), not deleted.
    from app.models.enrollment import Enrollment

    all_enrollments = db_session.query(Enrollment).filter(Enrollment.student_id == student.id).all()
    assert any(e.status == EnrollmentStatus.CLOSED for e in all_enrollments)


def test_confirm_promotion_blocked_on_capacity_conflict(db_session):
    ctx = _setup(db_session, section_capacity=5)
    student1 = _make_student(db_session, ctx, roll="R1", email="s1@example.com")
    student2 = _make_student(db_session, ctx, roll="R2", email="s2@example.com")
    # Target Section's own capacity (1) is smaller than the number of
    # students being promoted into it at once (2).
    target_semester, target_section = _promotion_target(db_session, ctx, capacity=1)

    with pytest.raises(ConflictError):
        enrollment_service.confirm_promotion(
            db_session,
            actor=ctx["admin"],
            student_ids=[student1.id, student2.id],
            to_batch_id=ctx["batch"].id,
            to_semester_no=target_semester.number,
            to_section_id=target_section.id,
        )


def test_preview_promotion_wrong_batch_rejected(db_session):
    """FR-ADM-006 Val ("no ... mismatches"): to_section_id's Semester must
    belong to to_batch_id. NEGATIVE: mismatched batch is rejected with zero
    writes."""
    ctx = _setup(db_session, section_capacity=5)
    student = _make_student(db_session, ctx)
    target_semester, target_section = _promotion_target(db_session, ctx)
    other_batch = academic_service.create_batch(
        db_session, actor=ctx["admin"], program_id=ctx["program"].id, start_year=2030, end_year=2034
    )
    before = _counts(db_session)

    with pytest.raises(ValidationError):
        enrollment_service.preview_promotion(
            db_session,
            student_ids=[student.id],
            to_batch_id=other_batch.id,
            to_semester_no=target_semester.number,
            to_section_id=target_section.id,
        )

    assert _counts(db_session) == before
    db_session.refresh(student)
    assert student.section_id == ctx["section"].id


def test_preview_promotion_wrong_semester_number_rejected(db_session):
    """NEGATIVE: to_semester_no not matching the target Section's actual
    Semester number is rejected with zero writes."""
    ctx = _setup(db_session, section_capacity=5)
    student = _make_student(db_session, ctx)
    target_semester, target_section = _promotion_target(db_session, ctx)
    before = _counts(db_session)

    with pytest.raises(ValidationError):
        enrollment_service.preview_promotion(
            db_session,
            student_ids=[student.id],
            to_batch_id=ctx["batch"].id,
            to_semester_no=target_semester.number + 1,
            to_section_id=target_section.id,
        )

    assert _counts(db_session) == before
    db_session.refresh(student)
    assert student.section_id == ctx["section"].id


def test_confirm_promotion_wrong_batch_rejected(db_session):
    """NEGATIVE: confirm_promotion inherits preview_promotion's guard - a
    mismatched batch is rejected with zero writes (no Enrollment/history/
    audit rows created, Student placement unchanged)."""
    ctx = _setup(db_session, section_capacity=5)
    student = _make_student(db_session, ctx)
    target_semester, target_section = _promotion_target(db_session, ctx)
    other_batch = academic_service.create_batch(
        db_session, actor=ctx["admin"], program_id=ctx["program"].id, start_year=2031, end_year=2035
    )
    before = _counts(db_session)

    with pytest.raises(ValidationError):
        enrollment_service.confirm_promotion(
            db_session,
            actor=ctx["admin"],
            student_ids=[student.id],
            to_batch_id=other_batch.id,
            to_semester_no=target_semester.number,
            to_section_id=target_section.id,
        )

    assert _counts(db_session) == before
    db_session.refresh(student)
    assert student.section_id == ctx["section"].id
    assert student.batch_id == ctx["batch"].id


def test_confirm_promotion_wrong_semester_number_rejected(db_session):
    """NEGATIVE: confirm_promotion rejects a mismatched to_semester_no with
    zero writes."""
    ctx = _setup(db_session, section_capacity=5)
    student = _make_student(db_session, ctx)
    target_semester, target_section = _promotion_target(db_session, ctx)
    before = _counts(db_session)

    with pytest.raises(ValidationError):
        enrollment_service.confirm_promotion(
            db_session,
            actor=ctx["admin"],
            student_ids=[student.id],
            to_batch_id=ctx["batch"].id,
            to_semester_no=target_semester.number + 1,
            to_section_id=target_section.id,
        )

    assert _counts(db_session) == before
    db_session.refresh(student)
    assert student.section_id == ctx["section"].id
    assert student.current_semester_no == 1


def test_promotion_unknown_student_not_found(db_session):
    ctx = _setup(db_session)
    with pytest.raises(NotFoundError):
        enrollment_service.preview_promotion(
            db_session,
            student_ids=[uuid.uuid4()],
            to_batch_id=ctx["batch"].id,
            to_semester_no=ctx["semester"].number,
            to_section_id=ctx["section"].id,
        )


def test_auto_enroll_writes_audit_log(db_session):
    ctx = _setup(db_session)
    student = _make_student(db_session, ctx)
    enrollment_service.auto_enroll_student(db_session, actor=ctx["admin"], student=student)

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "AUTO_ENROLL").all()
    assert len(logs) == 1
    assert logs[0].actor_id == ctx["admin"].id


def test_assign_elective_writes_audit_log(db_session):
    ctx = _setup(db_session)
    student = _make_student(db_session, ctx)
    enrollment_service.assign_elective(
        db_session,
        actor=ctx["admin"],
        student=student,
        elective_group_id=ctx["elective_group"].id,
        subject_id=ctx["elective_subject"].id,
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "ASSIGN_ELECTIVE").all()
    assert len(logs) == 1
    assert logs[0].actor_id == ctx["admin"].id


def test_confirm_promotion_writes_audit_log(db_session):
    ctx = _setup(db_session, section_capacity=5)
    student = _make_student(db_session, ctx)
    enrollment_service.auto_enroll_student(db_session, actor=ctx["admin"], student=student)
    target_semester, target_section = _promotion_target(db_session, ctx)
    operation_id = enrollment_service.confirm_promotion(
        db_session,
        actor=ctx["admin"],
        student_ids=[student.id],
        to_batch_id=ctx["batch"].id,
        to_semester_no=target_semester.number,
        to_section_id=target_section.id,
    )

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "CONFIRM_PROMOTION").all()
    assert len(logs) == 1
    assert logs[0].entity_id == str(operation_id)
