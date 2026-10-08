"""FR-STU-001 (read-only), FR-ADM-006. AC-002, AC-030. BUS-001."""

from __future__ import annotations

import datetime as dt

from app.core.security import hash_password
from app.models.student import Student
from app.models.subject import SubjectType
from app.models.subject_instance import TeacherAssignmentRole
from app.models.user import User, UserRole
from app.services import (
    academic_structure_service as academic_service,
)
from app.services import (
    assignment_service,
    enrollment_service,
    subject_instance_service,
    subject_service,
)


def _login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def _full_setup(db_session):
    admin = User(
        email="admin-enroll-setup@example.com",
        full_name="Admin",
        password_hash=hash_password("x"),
        role=UserRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    db_session.add(admin)
    db_session.commit()

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
        db_session, actor=admin, semester_id=semester.id, name="A", capacity=5
    )
    subject = subject_service.create_subject(
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
    teacher = User(
        email="teacher2@example.com",
        full_name="T",
        password_hash=hash_password("x"),
        role=UserRole.TEACHER,
        is_active=True,
        token_version=0,
    )
    db_session.add(teacher)
    db_session.commit()
    instance = subject_instance_service.create_subject_instance(
        db_session, actor=admin, subject_id=subject.id, section_id=section.id
    )
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

    student_user = User(
        email="student2@example.com",
        full_name="S",
        password_hash=hash_password("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
        token_version=0,
    )
    db_session.add(student_user)
    db_session.flush()
    student = Student(
        user_id=student_user.id,
        roll_number="R100",
        department_id=dept.id,
        batch_id=batch.id,
        section_id=section.id,
        current_semester_no=1,
    )
    db_session.add(student)
    db_session.commit()
    enrollment_service.auto_enroll_student(db_session, actor=admin, student=student)
    return student_user, student


def test_student_sees_own_enrollments(client, db_session):
    student_user, student = _full_setup(db_session)
    _login(client, "student2@example.com", "Secret123!")
    resp = client.get("/enrollments/me")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1


def test_student_enrollment_mutation_forbidden(client, db_session):
    """BUS-001/AC-002 negative: no mutation route exists for Student on
    enrollments - the admin-only sub-app requires ADMIN role."""
    student_user, student = _full_setup(db_session)
    _login(client, "student2@example.com", "Secret123!")
    resp = client.post(f"/admin/enrollments/auto-enroll/{student.id}", headers=_csrf_headers(client))
    assert resp.status_code == 403

    from app.models.enrollment import Enrollment

    count_before = db_session.query(Enrollment).count()
    assert count_before == 1  # unchanged by the forbidden attempt


def test_promotion_rejects_non_positive_target_semester(client, db_session):
    """to_semester_no must be > 0 (server-side, mirrors the UI min)."""
    _full_setup(db_session)
    _login(client, "admin-enroll-setup@example.com", "x")
    headers = _csrf_headers(client)
    uid = "00000000-0000-0000-0000-000000000001"
    for bad in (0, -1):
        payload = {
            "student_ids": [uid],
            "to_batch_id": uid,
            "to_semester_no": bad,
            "to_section_id": uid,
        }
        assert client.post(
            "/admin/enrollments/promotion/preview", json=payload, headers=headers
        ).status_code == 422
        assert client.post(
            "/admin/enrollments/promotion/confirm", json=payload, headers=headers
        ).status_code == 422
