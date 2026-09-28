"""Student CSV import - row-level atomic (ADR-0005). FR-ADM-005.

Each row is its own all-or-nothing unit (one SAVEPOINT per row, via
`db.begin_nested()`). Valid rows create a User+Student; invalid rows create
nothing and are reported with a row number and a named reason. The whole
file is rejected only when structurally unreadable (missing columns).
"""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.core.security import hash_password
from app.models.academic_structure import Batch, Department, Program, Section, Semester
from app.models.student import Student
from app.models.user import User, UserRole
from app.services import audit

REQUIRED_COLUMNS = {
    "roll_number",
    "email",
    "full_name",
    "department_code",
    "program_code",
    "batch_start_year",
    "current_semester_no",
    "section_name",
}

MAX_ROWS = 5000

# NFR-SEC uploads rule: MIME + extension validated server-side, in addition
# to the 25MB size limit enforced by the route.
ALLOWED_CONTENT_TYPES = {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}
ALLOWED_EXTENSIONS = {".csv"}


@dataclass
class ImportRowError:
    row_number: int
    reason: str


@dataclass
class ImportSummary:
    created: int = 0
    errors: list[ImportRowError] = field(default_factory=list)


def validate_upload(*, filename: str | None, content_type: str | None, size: int, max_bytes: int) -> None:
    """FR-ADM-005 / NFR-SEC uploads rule: server-side size + MIME/extension
    check. Raises `ValidationError` (not a raw `ValueError`) so `main.py`'s
    single exception-handler set maps it consistently, per the rework item
    that removed the route's ad-hoc `ValueError`."""
    if size > max_bytes:
        raise ValidationError(f"Uploaded file exceeds the {max_bytes // (1024 * 1024)}MB limit.")
    name = (filename or "").strip().lower()
    if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValidationError("Uploaded file must have a .csv extension.")
    if content_type is not None and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"Unsupported content type '{content_type}'; expected text/csv.")


def import_students_csv(db: Session, *, actor: User, csv_text: str) -> ImportSummary:
    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = set(reader.fieldnames or [])
    if not REQUIRED_COLUMNS.issubset(fieldnames):
        missing = sorted(REQUIRED_COLUMNS - fieldnames)
        raise ValidationError(f"CSV is missing required columns: {missing}")

    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise ValidationError(f"CSV exceeds the maximum of {MAX_ROWS} rows.")

    summary = ImportSummary()
    for idx, row in enumerate(rows, start=2):  # header occupies row 1
        savepoint = db.begin_nested()
        try:
            _import_one_row(db, actor=actor, row=row)
            savepoint.commit()
            summary.created += 1
        except Exception as exc:  # noqa: BLE001 - row-level isolation; continue to next row
            savepoint.rollback()
            summary.errors.append(ImportRowError(row_number=idx, reason=str(exc)))
    db.commit()
    return summary


def _import_one_row(db: Session, *, actor: User, row: dict) -> None:
    roll_number = (row.get("roll_number") or "").strip()
    email = (row.get("email") or "").strip().lower()
    full_name = (row.get("full_name") or "").strip()
    department_code = (row.get("department_code") or "").strip().upper()
    program_code = (row.get("program_code") or "").strip().upper()
    section_name = (row.get("section_name") or "").strip()

    if not all([roll_number, email, full_name, department_code, program_code, section_name]):
        raise ValueError("Missing required field(s).")

    try:
        batch_start_year = int(row["batch_start_year"])
        current_semester_no = int(row["current_semester_no"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("batch_start_year/current_semester_no must be integers.") from None

    if db.scalar(select(Student).where(Student.roll_number == roll_number)) is not None:
        raise ValueError(f"Duplicate roll_number '{roll_number}'.")
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise ValueError(f"Duplicate email '{email}'.")

    department = db.scalar(select(Department).where(Department.code == department_code))
    if department is None:
        raise ValueError(f"Unknown department_code '{department_code}'.")

    program = db.scalar(
        select(Program).where(Program.department_id == department.id, Program.code == program_code)
    )
    if program is None:
        raise ValueError(f"Unknown program_code '{program_code}' under department '{department_code}'.")

    batch = db.scalar(
        select(Batch).where(Batch.program_id == program.id, Batch.start_year == batch_start_year)
    )
    if batch is None:
        raise ValueError(f"Unknown batch starting {batch_start_year} for program '{program_code}'.")

    semester = db.scalar(
        select(Semester).where(Semester.batch_id == batch.id, Semester.number == current_semester_no)
    )
    if semester is None:
        raise ValueError(f"Unknown semester number {current_semester_no} for this batch.")

    section = db.scalar(
        select(Section).where(Section.semester_id == semester.id, Section.name == section_name)
    )
    if section is None:
        raise ValueError(f"Unknown section_name '{section_name}' for this semester.")

    current_count = (
        db.scalar(select(func.count()).select_from(Student).where(Student.section_id == section.id)) or 0
    )
    if current_count >= section.capacity:
        raise ValueError(f"Section '{section_name}' is at capacity.")

    user = User(
        email=email,
        full_name=full_name,
        role=UserRole.STUDENT,
        password_hash=hash_password(uuid.uuid4().hex),
        is_active=True,
        token_version=0,
    )
    db.add(user)
    db.flush()

    student = Student(
        user_id=user.id,
        roll_number=roll_number,
        department_id=department.id,
        batch_id=batch.id,
        section_id=section.id,
        current_semester_no=current_semester_no,
    )
    db.add(student)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="IMPORT_STUDENT",
        entity_type="Student",
        entity_id=student.id,
        after={"roll_number": roll_number, "email": email, "section_id": str(section.id)},
    )
