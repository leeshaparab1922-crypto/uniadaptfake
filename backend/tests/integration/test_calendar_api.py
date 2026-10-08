"""FR-ADM-007. AC-003."""

from __future__ import annotations

import datetime as dt

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service


def _admin_login(client, db_session):
    user = User(
        email="admin3@example.com",
        full_name="Admin",
        password_hash=hash_password("Secret123!"),
        role=UserRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    db_session.add(user)
    db_session.commit()
    client.post("/auth/login", json={"email": "admin3@example.com", "password": "Secret123!"})
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}, user


def _semester(db_session, admin):
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
    return academic_service.create_semester(
        db_session,
        actor=admin,
        batch_id=batch.id,
        number=1,
        start_date=dt.date(2024, 8, 1),
        end_date=dt.date(2024, 12, 20),
    )


def test_create_calendar_success(client, db_session):
    headers, admin = _admin_login(client, db_session)
    semester = _semester(db_session, admin)
    resp = client.post(
        "/admin/calendar",
        headers=headers,
        json={
            "semester_id": str(semester.id),
            "holidays": ["2024-10-02"],
            "ia_window_start": "2024-09-01",
            "ia_window_end": "2024-09-10",
            "practical_window_start": "2024-10-01",
            "practical_window_end": "2024-10-10",
            "university_exam_window_start": "2024-12-01",
            "university_exam_window_end": "2024-12-10",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 1


def test_create_calendar_window_outside_term_rejected(client, db_session):
    headers, admin = _admin_login(client, db_session)
    semester = _semester(db_session, admin)
    resp = client.post(
        "/admin/calendar",
        headers=headers,
        json={
            "semester_id": str(semester.id),
            "holidays": [],
            "ia_window_start": "2024-09-01",
            "ia_window_end": "2024-09-10",
            "practical_window_start": "2024-10-01",
            "practical_window_end": "2024-10-10",
            "university_exam_window_start": "2025-01-01",
            "university_exam_window_end": "2025-01-10",
        },
    )
    assert resp.status_code == 400


def test_timetable_slot_overlap_rejected(client, db_session):
    headers, admin = _admin_login(client, db_session)
    semester = _semester(db_session, admin)
    section = academic_service.create_section(
        db_session, actor=admin, semester_id=semester.id, name="A", capacity=10
    )

    first = client.post(
        "/admin/calendar/timetable-slots",
        headers=headers,
        json={
            "section_id": str(section.id),
            "day_of_week": 0,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "type": "CLASS",
            "effective_from": "2024-08-01",
        },
    )
    assert first.status_code == 200

    overlapping = client.post(
        "/admin/calendar/timetable-slots",
        headers=headers,
        json={
            "section_id": str(section.id),
            "day_of_week": 0,
            "start_time": "09:30:00",
            "end_time": "10:30:00",
            "type": "LAB",
            "effective_from": "2024-08-01",
        },
    )
    assert overlapping.status_code == 400
