"""Institute -> Department -> Program -> Batch -> Semester -> Section
hierarchy CRUD. FR-ADM-001.

ADR-0011: every create here takes the acting Admin as an explicit `actor`
and writes an `audit_logs` row in the same transaction.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.academic_structure import (
    Batch,
    Department,
    Institute,
    Program,
    Section,
    Semester,
)
from app.models.user import User
from app.services import audit


def create_institute(db: Session, *, actor: User, name: str, timezone: str) -> Institute:
    if not name.strip():
        raise ValidationError("Institute name is required.")
    institute = Institute(name=name.strip(), timezone=timezone)
    db.add(institute)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_INSTITUTE",
        entity_type="Institute",
        entity_id=institute.id,
        after={"name": institute.name, "timezone": institute.timezone},
    )
    db.commit()
    return institute


def create_department(
    db: Session, *, actor: User, institute_id: uuid.UUID, code: str, name: str
) -> Department:
    if db.get(Institute, institute_id) is None:
        raise NotFoundError("Institute not found.")
    code_norm = code.strip().upper()
    if not code_norm or not name.strip():
        raise ValidationError("Code and name are required.")
    exists = db.scalar(
        select(Department).where(Department.institute_id == institute_id, Department.code == code_norm)
    )
    if exists is not None:
        raise ValidationError(f"Department code '{code_norm}' already exists for this institute.")
    dept = Department(institute_id=institute_id, code=code_norm, name=name.strip())
    db.add(dept)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_DEPARTMENT",
        entity_type="Department",
        entity_id=dept.id,
        after={"institute_id": str(institute_id), "code": dept.code, "name": dept.name},
    )
    db.commit()
    return dept


def create_program(
    db: Session,
    *,
    actor: User,
    department_id: uuid.UUID,
    code: str,
    name: str,
    duration_semesters: int,
) -> Program:
    if db.get(Department, department_id) is None:
        raise NotFoundError("Department not found.")
    if duration_semesters <= 0:
        raise ValidationError("duration_semesters must be positive.")
    code_norm = code.strip().upper()
    exists = db.scalar(
        select(Program).where(Program.department_id == department_id, Program.code == code_norm)
    )
    if exists is not None:
        raise ValidationError(f"Program code '{code_norm}' already exists for this department.")
    program = Program(
        department_id=department_id,
        code=code_norm,
        name=name.strip(),
        duration_semesters=duration_semesters,
    )
    db.add(program)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_PROGRAM",
        entity_type="Program",
        entity_id=program.id,
        after={"department_id": str(department_id), "code": program.code, "name": program.name},
    )
    db.commit()
    return program


def create_batch(db: Session, *, actor: User, program_id: uuid.UUID, start_year: int, end_year: int) -> Batch:
    if db.get(Program, program_id) is None:
        raise NotFoundError("Program not found.")
    if start_year > end_year:
        raise ValidationError("start_year must not be after end_year.")
    exists = db.scalar(select(Batch).where(Batch.program_id == program_id, Batch.start_year == start_year))
    if exists is not None:
        raise ValidationError("A batch with this start_year already exists for this program.")
    batch = Batch(program_id=program_id, start_year=start_year, end_year=end_year)
    db.add(batch)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_BATCH",
        entity_type="Batch",
        entity_id=batch.id,
        after={"program_id": str(program_id), "start_year": start_year, "end_year": end_year},
    )
    db.commit()
    return batch


def create_semester(
    db: Session,
    *,
    actor: User,
    batch_id: uuid.UUID,
    number: int,
    start_date: date,
    end_date: date,
) -> Semester:
    if db.get(Batch, batch_id) is None:
        raise NotFoundError("Batch not found.")
    if number <= 0:
        raise ValidationError("Semester number must be positive.")
    if start_date >= end_date:
        raise ValidationError("start_date must precede end_date.")
    exists = db.scalar(select(Semester).where(Semester.batch_id == batch_id, Semester.number == number))
    if exists is not None:
        raise ValidationError("This semester number already exists for the batch.")
    semester = Semester(batch_id=batch_id, number=number, start_date=start_date, end_date=end_date)
    db.add(semester)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_SEMESTER",
        entity_type="Semester",
        entity_id=semester.id,
        after={
            "batch_id": str(batch_id),
            "number": number,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )
    db.commit()
    return semester


def create_section(db: Session, *, actor: User, semester_id: uuid.UUID, name: str, capacity: int) -> Section:
    """AC: a Section cannot be created without a valid semester/batch path."""
    semester = db.get(Semester, semester_id)
    if semester is None:
        raise NotFoundError("Semester not found; a Section requires a valid semester/batch path.")
    if capacity <= 0:
        raise ValidationError("capacity must be positive.")
    name_norm = name.strip()
    if not name_norm:
        raise ValidationError("Section name is required.")
    exists = db.scalar(select(Section).where(Section.semester_id == semester_id, Section.name == name_norm))
    if exists is not None:
        raise ValidationError(f"Section '{name_norm}' already exists for this semester.")
    section = Section(semester_id=semester_id, name=name_norm, capacity=capacity)
    db.add(section)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_SECTION",
        entity_type="Section",
        entity_id=section.id,
        after={"semester_id": str(semester_id), "name": name_norm, "capacity": capacity},
    )
    db.commit()
    return section


# --- Read-only list queries (FR-ADM-001 "view"). One query per level,
# optional parent filter, deterministic ordering (natural key, then id). ---


def list_institutes(db: Session) -> list[Institute]:
    return list(db.scalars(select(Institute).order_by(Institute.name, Institute.id)))


def list_departments(db: Session, *, institute_id: uuid.UUID | None = None) -> list[Department]:
    stmt = select(Department).order_by(Department.code, Department.id)
    if institute_id is not None:
        stmt = stmt.where(Department.institute_id == institute_id)
    return list(db.scalars(stmt))


def list_programs(db: Session, *, department_id: uuid.UUID | None = None) -> list[Program]:
    stmt = select(Program).order_by(Program.code, Program.id)
    if department_id is not None:
        stmt = stmt.where(Program.department_id == department_id)
    return list(db.scalars(stmt))


def list_batches(db: Session, *, program_id: uuid.UUID | None = None) -> list[Batch]:
    stmt = select(Batch).order_by(Batch.start_year, Batch.id)
    if program_id is not None:
        stmt = stmt.where(Batch.program_id == program_id)
    return list(db.scalars(stmt))


def list_semesters(db: Session, *, batch_id: uuid.UUID | None = None) -> list[Semester]:
    stmt = select(Semester).order_by(Semester.number, Semester.id)
    if batch_id is not None:
        stmt = stmt.where(Semester.batch_id == batch_id)
    return list(db.scalars(stmt))


def list_sections(db: Session, *, semester_id: uuid.UUID | None = None) -> list[Section]:
    stmt = select(Section).order_by(Section.name, Section.id)
    if semester_id is not None:
        stmt = stmt.where(Section.semester_id == semester_id)
    return list(db.scalars(stmt))
