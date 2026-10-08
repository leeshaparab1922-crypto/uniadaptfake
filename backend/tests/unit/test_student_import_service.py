"""FR-ADM-005. ADR-0005: row-level atomic CSV import."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.core.errors import ValidationError
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service
from app.services import student_import_service


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


def _setup(db_session, admin, capacity=1):
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
    academic_service.create_section(
        db_session, actor=admin, semester_id=semester.id, name="A", capacity=capacity
    )


CSV_HEADER = (
    "roll_number,email,full_name,department_code,program_code,"
    "batch_start_year,current_semester_no,section_name"
)


def test_missing_required_columns_raises(db_session):
    admin = _admin(db_session)
    with pytest.raises(ValidationError):
        student_import_service.import_students_csv(
            db_session, actor=admin, csv_text="roll_number,email\nR1,a@x.com\n"
        )


def test_mixed_valid_invalid_rows(db_session):
    admin = _admin(db_session)
    _setup(db_session, admin, capacity=5)
    csv_text = (
        CSV_HEADER + "\n"
        "R1,s1@example.com,Student One,CSE,BT,2024,1,A\n"
        "R2,not-an-email-row,Student Two,CSE,BT,not-an-int,1,A\n"
        "R1,dup@example.com,Duplicate Roll,CSE,BT,2024,1,A\n"
    )
    summary = student_import_service.import_students_csv(db_session, actor=admin, csv_text=csv_text)
    assert summary.created == 1
    assert len(summary.errors) == 2
    reasons = {e.row_number: e.reason for e in summary.errors}
    assert 3 in reasons and 4 in reasons  # header is row 1
    assert "roll_number" in reasons[4].lower() or "duplicate" in reasons[4].lower()


def test_invalid_row_creates_no_partial_record(db_session):
    admin = _admin(db_session)
    _setup(db_session, admin, capacity=5)
    csv_text = CSV_HEADER + "\n" + "R1,s1@example.com,Student One,UNKNOWN,BT,2024,1,A\n"
    summary = student_import_service.import_students_csv(db_session, actor=admin, csv_text=csv_text)
    assert summary.created == 0
    assert len(summary.errors) == 1

    from app.models.student import Student
    from app.models.user import User

    assert db_session.query(Student).count() == 0
    assert db_session.query(User).filter(User.email == "s1@example.com").count() == 0


def test_section_capacity_enforced(db_session):
    admin = _admin(db_session)
    _setup(db_session, admin, capacity=1)
    csv_text = (
        CSV_HEADER + "\n"
        "R1,s1@example.com,Student One,CSE,BT,2024,1,A\n"
        "R2,s2@example.com,Student Two,CSE,BT,2024,1,A\n"
    )
    summary = student_import_service.import_students_csv(db_session, actor=admin, csv_text=csv_text)
    assert summary.created == 1
    assert len(summary.errors) == 1
    assert "capacity" in summary.errors[0].reason.lower()


def test_validate_upload_rejects_oversized_file():
    with pytest.raises(ValidationError):
        student_import_service.validate_upload(
            filename="students.csv", content_type="text/csv", size=100, max_bytes=50
        )


def test_validate_upload_rejects_non_csv_extension():
    with pytest.raises(ValidationError):
        student_import_service.validate_upload(
            filename="students.txt", content_type="text/csv", size=10, max_bytes=1000
        )


def test_validate_upload_rejects_unsupported_content_type():
    with pytest.raises(ValidationError):
        student_import_service.validate_upload(
            filename="students.csv", content_type="application/json", size=10, max_bytes=1000
        )


def test_validate_upload_accepts_valid_csv():
    student_import_service.validate_upload(
        filename="students.csv", content_type="text/csv", size=10, max_bytes=1000
    )
