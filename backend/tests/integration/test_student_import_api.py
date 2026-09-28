"""FR-ADM-005. ADR-0005."""

from __future__ import annotations

import datetime as dt
import io

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service


def _admin_login(client, db_session):
    user = User(
        email="admin4@example.com",
        full_name="Admin",
        password_hash=hash_password("Secret123!"),
        role=UserRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    db_session.add(user)
    db_session.commit()
    client.post("/auth/login", json={"email": "admin4@example.com", "password": "Secret123!"})
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}, user


def _setup_structure(db_session, admin):
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
    academic_service.create_section(db_session, actor=admin, semester_id=semester.id, name="A", capacity=5)


def test_mixed_valid_invalid_rows_via_api(client, db_session):
    headers, admin = _admin_login(client, db_session)
    _setup_structure(db_session, admin)

    csv_content = (
        "roll_number,email,full_name,department_code,program_code,batch_start_year,current_semester_no,section_name\n"
        "R1,s1@example.com,Student One,CSE,BT,2024,1,A\n"
        "R2,bad,Student Two,UNKNOWN,BT,2024,1,A\n"
    )
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/admin/students/import", headers=headers, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row_number"] == 3


def test_import_forbidden_without_csrf(client, db_session):
    _, admin = _admin_login(client, db_session)
    _setup_structure(db_session, admin)
    csv_content = (
        "roll_number,email,full_name,department_code,program_code,"
        "batch_start_year,current_semester_no,section_name\n"
    )
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/admin/students/import", files=files)
    assert resp.status_code == 403


def test_import_rejects_non_csv_extension(client, db_session):
    """Rework item 6 negative: server-side MIME/extension check, in
    addition to the size limit, rejects a non-.csv upload even when the
    browser-supplied content-type looks plausible."""
    headers, admin = _admin_login(client, db_session)
    _setup_structure(db_session, admin)
    csv_content = "roll_number,email,full_name,department_code,program_code,batch_start_year,current_semester_no,section_name\n"
    files = {"file": ("students.txt", io.BytesIO(csv_content.encode("utf-8")), "text/plain")}
    resp = client.post("/admin/students/import", headers=headers, files=files)
    assert resp.status_code == 400


def test_import_writes_audit_log_per_created_row(client, db_session):
    headers, admin = _admin_login(client, db_session)
    _setup_structure(db_session, admin)
    csv_content = (
        "roll_number,email,full_name,department_code,program_code,batch_start_year,current_semester_no,section_name\n"
        "R1,s1@example.com,Student One,CSE,BT,2024,1,A\n"
    )
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/admin/students/import", headers=headers, files=files)
    assert resp.status_code == 200

    from app.models.audit_log import AuditLog

    logs = db_session.query(AuditLog).filter(AuditLog.action == "IMPORT_STUDENT").all()
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
