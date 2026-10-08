"""Subject/Unit catalogue. FR-ADM-003. Unit weight sum-to-100 invariant per
ADR-0002: enforced here under a Subject row lock, not as a database CHECK
(Postgres cannot express a cross-row SUM constraint portably).

ADR-0011: every mutation here takes the acting Admin as an explicit `actor`
and writes an `audit_logs` row in the same transaction.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.academic_structure import Program
from app.models.subject import ElectiveGroup, Subject, SubjectType, Unit
from app.models.user import User
from app.services import audit

SUPPORTED_TYPES = {SubjectType.CORE, SubjectType.ELECTIVE, SubjectType.LAB}


def create_elective_group(
    db: Session,
    *,
    actor: User,
    program_id: uuid.UUID,
    semester_no: int,
    name: str,
    required: bool,
) -> ElectiveGroup:
    if db.get(Program, program_id) is None:
        raise NotFoundError("Program not found.")
    if not name.strip():
        raise ValidationError("Elective group name is required.")
    group = ElectiveGroup(
        program_id=program_id,
        semester_no=semester_no,
        name=name.strip(),
        required=required,
    )
    db.add(group)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_ELECTIVE_GROUP",
        entity_type="ElectiveGroup",
        entity_id=group.id,
        after={"program_id": str(program_id), "semester_no": semester_no, "name": group.name},
    )
    db.commit()
    return group


def create_subject(
    db: Session,
    *,
    actor: User,
    program_id: uuid.UUID,
    semester_no: int,
    code: str,
    name: str,
    credits: int,
    type_: SubjectType,
    elective_group_id: uuid.UUID | None,
) -> Subject:
    if db.get(Program, program_id) is None:
        raise NotFoundError("Program not found.")
    if credits < 0:
        raise ValidationError("credits must be nonnegative.")
    if type_ not in SUPPORTED_TYPES:
        raise ValidationError(f"Unsupported subject type '{type_}'.")

    code_norm = code.strip().upper()
    if not code_norm or not name.strip():
        raise ValidationError("Code and name are required.")
    exists = db.scalar(
        select(Subject).where(
            Subject.program_id == program_id,
            Subject.semester_no == semester_no,
            Subject.code == code_norm,
        )
    )
    if exists is not None:
        raise ValidationError(f"Subject code '{code_norm}' already exists for this program/semester.")

    if type_ == SubjectType.ELECTIVE and elective_group_id is None:
        raise ValidationError("ELECTIVE subjects must belong to an elective group.")
    if type_ != SubjectType.ELECTIVE and elective_group_id is not None:
        raise ValidationError("Only ELECTIVE subjects may belong to an elective group.")
    if elective_group_id is not None:
        group = db.get(ElectiveGroup, elective_group_id)
        if group is None:
            raise NotFoundError("Elective group not found.")
        if group.program_id != program_id or group.semester_no != semester_no:
            raise ValidationError("Elective group must belong to the same program/semester as the subject.")

    subject = Subject(
        program_id=program_id,
        semester_no=semester_no,
        code=code_norm,
        name=name.strip(),
        credits=credits,
        type=type_,
        elective_group_id=elective_group_id,
    )
    db.add(subject)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_SUBJECT",
        entity_type="Subject",
        entity_id=subject.id,
        after={
            "program_id": str(program_id),
            "semester_no": semester_no,
            "code": subject.code,
            "type": type_.value,
        },
    )
    db.commit()
    return subject


def set_units(db: Session, *, actor: User, subject_id: uuid.UUID, units: Sequence[dict]) -> list[Unit]:
    """Replaces a Subject's Units atomically under a row lock (ADR-0002).

    `units` items: {"order_index": int, "name": str, "weightage": int}.
    Each weight must be 0..100 and the set must sum to exactly 100.

    The `SELECT ... FOR UPDATE` row lock is skipped on SQLite (used only by
    this phase's test suite, since Docker/Postgres are unavailable in this
    environment - see the "Test environment" note in plan.md) because
    SQLite has no row-level locking; production always runs on Postgres 15,
    where the lock applies exactly as ADR-0002 specifies.
    """
    query = select(Subject).where(Subject.id == subject_id)
    if db.bind is not None and db.bind.dialect.name != "sqlite":
        query = query.with_for_update()
    subject = db.execute(query).scalar_one_or_none()
    if subject is None:
        raise NotFoundError("Subject not found.")
    if not units:
        raise ValidationError("At least one Unit is required.")

    total = 0
    for u in units:
        weight = u["weightage"]
        if weight < 0 or weight > 100:
            raise ValidationError(f"Unit '{u.get('name')}' weightage must be between 0 and 100.")
        total += weight
    if total != 100:
        raise ValidationError(f"Unit weights must sum to exactly 100 (got {total}).")

    db.execute(Unit.__table__.delete().where(Unit.subject_id == subject_id))
    db.flush()
    created: list[Unit] = []
    for u in units:
        unit = Unit(
            subject_id=subject_id,
            order_index=u["order_index"],
            name=u["name"].strip(),
            weightage=u["weightage"],
        )
        db.add(unit)
        created.append(unit)
    audit.record(
        db,
        actor=actor,
        action="SET_UNITS",
        entity_type="Subject",
        entity_id=subject_id,
        after={"unit_count": len(created), "total_weight": total},
    )
    db.commit()
    for unit in created:
        db.refresh(unit)
    return created
