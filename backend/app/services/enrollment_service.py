"""Auto-enrollment, elective allocation, and promotion/transfer
preview+confirm. FR-ADM-006.

BUS-001: Students never manually select/add/drop subjects - there is no
mutation entry point here that a Student can reach; every function takes
an Admin `actor` or is called from an Admin-only route.
BUS-002: Enrollment is auto-derived from Program+Semester+Section; Admin
assigns exactly one eligible Subject per required elective group, within
capacity.
BUS-049: promotion/transfer previews the new authoritative set before
confirmation and preserves historical enrollments (never erases them).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.academic_structure import Batch, Section, Semester
from app.models.enrollment import Enrollment, EnrollmentStatus, StudentPlacementHistory
from app.models.student import Student
from app.models.subject import ElectiveGroup, Subject, SubjectType
from app.models.subject_instance import SubjectInstance, SubjectInstanceStatus
from app.models.user import User
from app.services import audit


def _active_instances_for_placement(
    db: Session, *, program_id: uuid.UUID, semester_no: int, section_id: uuid.UUID
) -> list[SubjectInstance]:
    return list(
        db.scalars(
            select(SubjectInstance)
            .join(Subject, Subject.id == SubjectInstance.subject_id)
            .where(
                SubjectInstance.section_id == section_id,
                SubjectInstance.status == SubjectInstanceStatus.ACTIVE,
                Subject.program_id == program_id,
                Subject.semester_no == semester_no,
            )
        ).all()
    )


def _auto_enroll_student_no_commit(db: Session, *, student: Student) -> list[Enrollment]:
    """Internal, no-commit variant so `confirm_promotion` can compose this
    step inside its own single atomic transaction."""
    batch = db.get(Batch, student.batch_id)
    instances = _active_instances_for_placement(
        db,
        program_id=batch.program_id,
        semester_no=student.current_semester_no,
        section_id=student.section_id,
    )
    created: list[Enrollment] = []
    today = date.today()
    for instance in instances:
        subject = db.get(Subject, instance.subject_id)
        if subject.type == SubjectType.ELECTIVE:
            continue  # Electives require an explicit Admin selection (BUS-002).
        existing = db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.subject_instance_id == instance.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        if existing is not None:
            continue  # Idempotent: re-running creates no duplicate active rows.
        enrollment = Enrollment(
            student_id=student.id,
            subject_instance_id=instance.id,
            elective_group_id=None,
            status=EnrollmentStatus.ACTIVE,
            auto_allocated=True,
            effective_from=today,
        )
        db.add(enrollment)
        created.append(enrollment)
    db.flush()
    return created


def auto_enroll_student(db: Session, *, actor: User, student: Student) -> list[Enrollment]:
    """Auto-derives Enrollment rows for every active, non-elective
    SubjectInstance matching the Student's current Program+Semester+Section.

    ADR-0011: FR-ADM-006's Post ("allocation is audited") - one audit row
    per invocation, referencing every Enrollment created."""
    created = _auto_enroll_student_no_commit(db, student=student)
    if created:
        db.flush()
        audit.record(
            db,
            actor=actor,
            action="AUTO_ENROLL",
            entity_type="Student",
            entity_id=student.id,
            after={"enrollment_ids": [str(e.id) for e in created]},
        )
    db.commit()
    return created


def assign_elective(
    db: Session,
    *,
    actor: User,
    student: Student,
    elective_group_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> Enrollment:
    """Admin assigns exactly one eligible Subject per required elective
    group, within the Section-level SubjectInstance capacity."""
    group = db.get(ElectiveGroup, elective_group_id)
    if group is None:
        raise NotFoundError("Elective group not found.")
    subject = db.get(Subject, subject_id)
    if subject is None or subject.elective_group_id != elective_group_id:
        raise ValidationError("Subject does not belong to this elective group.")

    instance = db.scalar(
        select(SubjectInstance).where(
            SubjectInstance.subject_id == subject_id,
            SubjectInstance.section_id == student.section_id,
            SubjectInstance.status == SubjectInstanceStatus.ACTIVE,
        )
    )
    if instance is None:
        raise NotFoundError("No active SubjectInstance for this Subject in the Student's Section.")

    section = db.get(Section, student.section_id)
    current_count = (
        db.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(
                Enrollment.subject_instance_id == instance.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        or 0
    )

    existing_in_group = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.elective_group_id == elective_group_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    if existing_in_group is not None and existing_in_group.subject_instance_id == instance.id:
        return existing_in_group  # Idempotent no-op: same selection re-submitted.
    if current_count >= section.capacity:
        raise ConflictError("This elective's Section-level capacity is full.")

    if existing_in_group is not None:
        existing_in_group.status = EnrollmentStatus.CLOSED
        existing_in_group.effective_to = date.today()

    enrollment = Enrollment(
        student_id=student.id,
        subject_instance_id=instance.id,
        elective_group_id=elective_group_id,
        status=EnrollmentStatus.ACTIVE,
        auto_allocated=True,
        effective_from=date.today(),
    )
    db.add(enrollment)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="ASSIGN_ELECTIVE",
        entity_type="Enrollment",
        entity_id=enrollment.id,
        after={
            "student_id": str(student.id),
            "elective_group_id": str(elective_group_id),
            "subject_id": str(subject_id),
        },
    )
    db.commit()
    return enrollment


def get_active_enrollments(db: Session, *, student_id: uuid.UUID) -> list[Enrollment]:
    """FR-STU-001: read-only. No route may call this from a mutation path."""
    return list(
        db.scalars(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        ).all()
    )


def required_electives_missing(db: Session, *, student: Student) -> list[ElectiveGroup]:
    """Required elective groups (for the Student's program/semester) with no
    active selection yet."""
    batch = db.get(Batch, student.batch_id)
    groups = db.scalars(
        select(ElectiveGroup).where(
            ElectiveGroup.program_id == batch.program_id,
            ElectiveGroup.semester_no == student.current_semester_no,
            ElectiveGroup.required.is_(True),
        )
    ).all()
    missing = []
    for group in groups:
        has_selection = db.scalar(
            select(Enrollment.id).where(
                Enrollment.student_id == student.id,
                Enrollment.elective_group_id == group.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        if has_selection is None:
            missing.append(group)
    return missing


@dataclass
class PromotionPreviewItem:
    student_id: uuid.UUID
    roll_number: str
    from_section_id: uuid.UUID
    to_section_id: uuid.UUID
    capacity_conflict: bool


@dataclass
class PromotionPreview:
    items: list[PromotionPreviewItem] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return any(item.capacity_conflict for item in self.items)


def preview_promotion(
    db: Session,
    *,
    student_ids: list[uuid.UUID],
    to_batch_id: uuid.UUID,
    to_semester_no: int,
    to_section_id: uuid.UUID,
) -> PromotionPreview:
    """Read-only: computes the proposed placement and any capacity
    conflicts. Performs zero writes (BUS-049/AC-030)."""
    section = db.get(Section, to_section_id)
    if section is None:
        raise NotFoundError("Target Section not found.")

    semester = db.get(Semester, section.semester_id)
    if semester is None or semester.batch_id != to_batch_id or semester.number != to_semester_no:
        # FR-ADM-006 Val: "no ... mismatches" - to_section_id's own Semester
        # must actually belong to to_batch_id and carry number to_semester_no.
        # Checked here (preview_promotion) so confirm_promotion, which calls
        # this function first, inherits the same guard with zero writes.
        raise ValidationError(
            "Target Section's Semester does not match the given to_batch_id/to_semester_no."
        )

    existing_count = (
        db.scalar(select(func.count()).select_from(Student).where(Student.section_id == to_section_id)) or 0
    )

    preview = PromotionPreview()
    projected = existing_count
    for student_id in student_ids:
        student = db.get(Student, student_id)
        if student is None:
            raise NotFoundError(f"Student {student_id} not found.")
        already_in_target = student.section_id == to_section_id
        if not already_in_target:
            projected += 1
        preview.items.append(
            PromotionPreviewItem(
                student_id=student.id,
                roll_number=student.roll_number,
                from_section_id=student.section_id,
                to_section_id=to_section_id,
                capacity_conflict=projected > section.capacity,
            )
        )
    return preview


def confirm_promotion(
    db: Session,
    *,
    actor: User,
    student_ids: list[uuid.UUID],
    to_batch_id: uuid.UUID,
    to_semester_no: int,
    to_section_id: uuid.UUID,
) -> uuid.UUID:
    """Atomically moves Students, closes prior active enrollments (history
    preserved via `student_placement_history`, not erased), and re-derives
    enrollment for the new placement - all in one transaction. Blocked
    entirely if the preview shows any capacity conflict."""
    preview = preview_promotion(
        db,
        student_ids=student_ids,
        to_batch_id=to_batch_id,
        to_semester_no=to_semester_no,
        to_section_id=to_section_id,
    )
    if preview.has_conflicts:
        raise ConflictError("Target Section capacity would be exceeded; promotion blocked.")

    operation_id = uuid.uuid4()
    today = date.today()
    for item in preview.items:
        student = db.get(Student, item.student_id)
        from_batch_id = student.batch_id
        from_semester_no = student.current_semester_no
        from_section_id = student.section_id

        active_enrollments = db.scalars(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        ).all()
        for enrollment in active_enrollments:
            enrollment.status = EnrollmentStatus.CLOSED
            enrollment.effective_to = today

        student.batch_id = to_batch_id
        student.current_semester_no = to_semester_no
        student.section_id = to_section_id

        db.add(
            StudentPlacementHistory(
                student_id=student.id,
                from_batch_id=from_batch_id,
                to_batch_id=to_batch_id,
                from_semester_no=from_semester_no,
                to_semester_no=to_semester_no,
                from_section_id=from_section_id,
                to_section_id=to_section_id,
                effective_date=today,
                actor_id=actor.id,
                operation_id=operation_id,
            )
        )
        db.flush()
        _auto_enroll_student_no_commit(db, student=student)

    audit.record(
        db,
        actor=actor,
        action="CONFIRM_PROMOTION",
        entity_type="PromotionOperation",
        entity_id=operation_id,
        after={
            "student_ids": [str(s) for s in student_ids],
            "to_batch_id": str(to_batch_id),
            "to_semester_no": to_semester_no,
            "to_section_id": str(to_section_id),
        },
    )
    db.commit()
    return operation_id
