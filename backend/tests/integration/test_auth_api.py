"""AC-001 (RBAC/scope), AC-029 (session/security). FR-AUTH-001..004."""

from __future__ import annotations

import datetime as dt

from app.core.security import hash_password
from app.models.student import Student
from app.models.subject import SubjectType
from app.models.subject_instance import TeacherAssignmentRole
from app.models.user import User, UserRole
from app.services import (
    academic_structure_service,
    assignment_service,
    subject_instance_service,
    subject_service,
)


def _create_user(db_session, *, email, password, role, active=True) -> User:
    user = User(
        email=email,
        full_name="Test",
        password_hash=hash_password(password),
        role=role,
        is_active=active,
        token_version=0,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_success_sets_cookies(client, db_session):
    _create_user(db_session, email="admin@example.com", password="Secret123!", role=UserRole.ADMIN)
    resp = _login(client, "admin@example.com", "Secret123!")
    assert resp.status_code == 200
    assert "uniadapt_session" in resp.cookies
    assert "csrf_token" in resp.cookies


def test_login_wrong_password_generic_401(client, db_session):
    _create_user(db_session, email="admin@example.com", password="Secret123!", role=UserRole.ADMIN)
    resp = _login(client, "admin@example.com", "wrong")
    assert resp.status_code == 401


def test_login_unknown_account_same_generic_401(client, db_session):
    resp = _login(client, "nobody@example.com", "whatever")
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_after_login(client, db_session):
    _create_user(db_session, email="admin@example.com", password="Secret123!", role=UserRole.ADMIN)
    _login(client, "admin@example.com", "Secret123!")
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@example.com"


def test_logout_without_csrf_header_rejected(client, db_session):
    _create_user(db_session, email="admin@example.com", password="Secret123!", role=UserRole.ADMIN)
    _login(client, "admin@example.com", "Secret123!")
    resp = client.post("/auth/logout")
    assert resp.status_code == 403


def test_logout_revokes_session_immediately(client, db_session):
    _create_user(db_session, email="admin@example.com", password="Secret123!", role=UserRole.ADMIN)
    _login(client, "admin@example.com", "Secret123!")
    csrf = client.cookies.get("csrf_token")
    resp = client.post("/auth/logout", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200

    # The old session cookie the client still has recorded (pre-logout JWT) must now be rejected.
    resp2 = client.get("/auth/me")
    assert resp2.status_code == 401


def test_deactivated_account_cannot_login(client, db_session):
    _create_user(
        db_session, email="gone@example.com", password="Secret123!", role=UserRole.STUDENT, active=False
    )
    resp = _login(client, "gone@example.com", "Secret123!")
    assert resp.status_code == 401


def test_role_scope_enforcement_teacher_cannot_reach_admin_routes(client, db_session):
    _create_user(db_session, email="teacher@example.com", password="Secret123!", role=UserRole.TEACHER)
    _login(client, "teacher@example.com", "Secret123!")
    resp = client.post(
        "/admin/accounts", json={"email": "x@example.com", "full_name": "X", "role": "STUDENT"}
    )
    assert resp.status_code == 403


def test_role_scope_enforcement(client, db_session):
    """AC-001 positive+negative: a Teacher assigned to Section A's
    SubjectInstance sees only Section A's Students; requesting Section B
    (unassigned) returns 403/404 with no data."""
    admin = _create_user(db_session, email="admin2@example.com", password="Secret123!", role=UserRole.ADMIN)
    teacher = _create_user(
        db_session, email="teach2@example.com", password="Secret123!", role=UserRole.TEACHER
    )

    institute = academic_structure_service.create_institute(
        db_session, actor=admin, name="Inst", timezone="Asia/Kolkata"
    )
    dept = academic_structure_service.create_department(
        db_session, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = academic_structure_service.create_program(
        db_session, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    batch = academic_structure_service.create_batch(
        db_session, actor=admin, program_id=program.id, start_year=2024, end_year=2028
    )
    semester = academic_structure_service.create_semester(
        db_session,
        actor=admin,
        batch_id=batch.id,
        number=1,
        start_date=dt.date(2024, 8, 1),
        end_date=dt.date(2024, 12, 1),
    )
    section_a = academic_structure_service.create_section(
        db_session, actor=admin, semester_id=semester.id, name="A", capacity=60
    )
    section_b = academic_structure_service.create_section(
        db_session, actor=admin, semester_id=semester.id, name="B", capacity=60
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
    instance_a = subject_instance_service.create_subject_instance(
        db_session, actor=admin, subject_id=subject.id, section_id=section_a.id
    )
    assignment_service.assign_teacher(
        db_session,
        actor=admin,
        teacher_id=teacher.id,
        subject_instance_id=instance_a.id,
        role=TeacherAssignmentRole.PRIMARY,
    )

    student_a_user = _create_user(
        db_session, email="student-a@example.com", password="Secret123!", role=UserRole.STUDENT
    )
    student_a = Student(
        user_id=student_a_user.id,
        roll_number="RA1",
        department_id=dept.id,
        batch_id=batch.id,
        section_id=section_a.id,
        current_semester_no=1,
    )
    db_session.add(student_a)
    db_session.commit()

    _login(client, "teach2@example.com", "Secret123!")

    resp_a = client.get(f"/teacher/sections/{section_a.id}/students")
    assert resp_a.status_code == 200
    body = resp_a.json()
    assert len(body) == 1
    assert body[0]["roll_number"] == "RA1"

    resp_b = client.get(f"/teacher/sections/{section_b.id}/students")
    assert resp_b.status_code in (403, 404)
    assert resp_b.json().get("roll_number") is None


def test_login_throttled_after_repeated_failures(client, db_session):
    from app.core.config import settings

    _create_user(db_session, email="admin@example.com", password="Secret123!", role=UserRole.ADMIN)
    limit = settings.rate_limit_login_per_account_per_window
    for _ in range(limit):
        resp = _login(client, "admin@example.com", "wrong")
        assert resp.status_code == 401
    resp = _login(client, "admin@example.com", "wrong")
    assert resp.status_code == 429
