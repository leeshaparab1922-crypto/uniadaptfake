"""SubjectInstance mapping (Subject offered to a Section) and activation
gate. FR-ADM-004.

ADR-0011: both mutations here take the acting Admin as an explicit `actor`
and write an `audit_logs` row in the same transaction.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.academic_structure import Batch, Section, Semester
from app.models.subject import Subject
from app.models.subject_instance import (
    SubjectInstance,
    SubjectInstanceStatus,
    TeacherAssignment,
)
from app.models.user import User
from app.services import audit


def create_subject_instance(
    db: Session, *, actor: User, subject_id: uuid.UUID, section_id: uuid.UUID
) -> SubjectInstance:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise NotFoundError("Subject not found.")
    section = db.get(Section, section_id)
    if section is None:
        raise NotFoundError("Section not found.")
    semester = db.get(Semester, section.semester_id)
    batch = db.get(Batch, semester.batch_id)
    if batch.program_id != subject.program_id or semester.number != subject.semester_no:
        raise ValidationError("Subject's Program/Semester must match the Section's Program/Semester path.")

    existing = db.scalar(
        select(SubjectInstance).where(
            SubjectInstance.subject_id == subject_id,
            SubjectInstance.section_id == section_id,
        )
    )
    if existing is not None:
        raise ValidationError("A SubjectInstance already exists for this Subject and Section.")

    instance = SubjectInstance(
        subject_id=subject_id, section_id=section_id, status=SubjectInstanceStatus.DRAFT
    )
    db.add(instance)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="CREATE_SUBJECT_INSTANCE",
        entity_type="SubjectInstance",
        entity_id=instance.id,
        after={"subject_id": str(subject_id), "section_id": str(section_id)},
    )
    db.commit()
    return instance


def activate_subject_instance(db: Session, *, actor: User, subject_instance_id: uuid.UUID) -> SubjectInstance:
    """Val (FR-ADM-004): at least one assigned Teacher before activation."""
    instance = db.get(SubjectInstance, subject_instance_id)
    if instance is None:
        raise NotFoundError("SubjectInstance not found.")
    has_teacher = db.scalar(
        select(TeacherAssignment.id).where(TeacherAssignment.subject_instance_id == instance.id)
    )
    if has_teacher is None:
        raise ValidationError("At least one Teacher must be assigned before activation.")
    before = {"status": instance.status.value}
    instance.status = SubjectInstanceStatus.ACTIVE
    audit.record(
        db,
        actor=actor,
        action="ACTIVATE_SUBJECT_INSTANCE",
        entity_type="SubjectInstance",
        entity_id=instance.id,
        before=before,
        after={"status": SubjectInstanceStatus.ACTIVE.value},
    )
    db.commit()
    return instance
