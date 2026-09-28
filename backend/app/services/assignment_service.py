"""Teacher assignment and Subject Owner invariants. FR-ADM-002.

ADR-0003: exactly one owner per Subject via a unique index on `subject_id`;
owner changes update the row in place and write an `audit_logs` entry in
the same transaction. Owner must be an active TEACHER who is PRIMARY on at
least one instance of the Subject.

ADR-0011: every mutation here takes the acting Admin as an explicit
`actor` and writes an `audit_logs` row (via the shared `app.services.audit`
helper) in the same transaction as the mutation.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.subject import Subject
from app.models.subject_instance import (
    SubjectInstance,
    SubjectInstanceStatus,
    SubjectOwnerAssignment,
    TeacherAssignment,
    TeacherAssignmentRole,
)
from app.models.user import User, UserRole
from app.services import audit


def assign_teacher(
    db: Session,
    *,
    actor: User,
    teacher_id: uuid.UUID,
    subject_instance_id: uuid.UUID,
    role: TeacherAssignmentRole,
) -> TeacherAssignment:
    teacher = db.get(User, teacher_id)
    if teacher is None or teacher.role != UserRole.TEACHER or not teacher.is_active:
        raise ValidationError("Assignee must be an active account with role TEACHER.")
    instance = db.get(SubjectInstance, subject_instance_id)
    if instance is None:
        raise NotFoundError("SubjectInstance not found.")

    existing = db.scalar(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == teacher_id,
            TeacherAssignment.subject_instance_id == subject_instance_id,
        )
    )
    if existing is not None:
        before = {"role": existing.role.value}
        existing.role = role
        audit.record(
            db,
            actor=actor,
            action="ASSIGN_TEACHER",
            entity_type="TeacherAssignment",
            entity_id=existing.id,
            before=before,
            after={"role": role.value},
        )
        db.commit()
        return existing

    assignment = TeacherAssignment(teacher_id=teacher_id, subject_instance_id=subject_instance_id, role=role)
    db.add(assignment)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="ASSIGN_TEACHER",
        entity_type="TeacherAssignment",
        entity_id=assignment.id,
        after={
            "teacher_id": str(teacher_id),
            "subject_instance_id": str(subject_instance_id),
            "role": role.value,
        },
    )
    db.commit()
    return assignment


def set_subject_owner(
    db: Session,
    *,
    actor: User,
    subject_id: uuid.UUID,
    owner_teacher_id: uuid.UUID,
    reason: str | None = None,
) -> SubjectOwnerAssignment:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise NotFoundError("Subject not found.")
    teacher = db.get(User, owner_teacher_id)
    if teacher is None or teacher.role != UserRole.TEACHER or not teacher.is_active:
        raise ValidationError("Owner must be an active account with role TEACHER.")

    is_primary_somewhere = db.scalar(
        select(TeacherAssignment.id)
        .join(SubjectInstance, SubjectInstance.id == TeacherAssignment.subject_instance_id)
        .where(
            SubjectInstance.subject_id == subject_id,
            TeacherAssignment.teacher_id == owner_teacher_id,
            TeacherAssignment.role == TeacherAssignmentRole.PRIMARY,
        )
    )
    if is_primary_somewhere is None:
        raise ValidationError("Owner must be PRIMARY on at least one instance of this Subject.")

    existing = db.scalar(
        select(SubjectOwnerAssignment).where(SubjectOwnerAssignment.subject_id == subject_id)
    )
    before = None
    if existing is not None:
        before = {"owner_teacher_id": str(existing.owner_teacher_id)}
        existing.owner_teacher_id = owner_teacher_id
        owner_row = existing
    else:
        owner_row = SubjectOwnerAssignment(subject_id=subject_id, owner_teacher_id=owner_teacher_id)
        db.add(owner_row)

    audit.record(
        db,
        actor=actor,
        action="SET_SUBJECT_OWNER",
        entity_type="Subject",
        entity_id=subject_id,
        before=before,
        after={"owner_teacher_id": str(owner_teacher_id)},
        reason=reason,
    )
    db.commit()
    return owner_row


def active_instances_missing_teacher(
    db: Session, *, subject_id: uuid.UUID | None = None
) -> list[SubjectInstance]:
    """Every active SubjectInstance must have at least one Teacher assignment."""
    query = select(SubjectInstance).where(SubjectInstance.status == SubjectInstanceStatus.ACTIVE)
    if subject_id is not None:
        query = query.where(SubjectInstance.subject_id == subject_id)
    instances = db.scalars(query).all()
    missing = []
    for instance in instances:
        has_teacher = db.scalar(
            select(TeacherAssignment.id).where(TeacherAssignment.subject_instance_id == instance.id)
        )
        if has_teacher is None:
            missing.append(instance)
    return missing
