"""SubjectInstance (Subject offered to a Section), TeacherAssignment, and
SubjectOwnerAssignment. FR-ADM-002, FR-ADM-004.

ADR-0003: exactly one owner per Subject is enforced by a unique index on
`subject_id` alone; owner changes update the row in place and write an
`audit_logs` entry in the same transaction (see `assignment_service`).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SubjectInstanceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"


class TeacherAssignmentRole(str, enum.Enum):
    PRIMARY = "PRIMARY"
    CO = "CO"


class SubjectInstance(Base, TimestampMixin):
    __tablename__ = "subject_instances"
    __table_args__ = (
        UniqueConstraint(
            "subject_id", "section_id", name="uq_subject_instance_per_section"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sections.id", ondelete="RESTRICT"), nullable=False
    )
    exam_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[SubjectInstanceStatus] = mapped_column(
        SAEnum(
            SubjectInstanceStatus,
            name="subject_instance_status",
            native_enum=False,
            create_constraint=True,
            length=8,
        ),
        nullable=False,
        default=SubjectInstanceStatus.DRAFT,
    )


class TeacherAssignment(Base, TimestampMixin):
    __tablename__ = "teacher_assignments"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "subject_instance_id", name="uq_teacher_per_instance"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    subject_instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_instances.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[TeacherAssignmentRole] = mapped_column(
        SAEnum(
            TeacherAssignmentRole,
            name="teacher_assignment_role",
            native_enum=False,
            create_constraint=True,
            length=8,
        ),
        nullable=False,
    )


class SubjectOwnerAssignment(Base, TimestampMixin):
    __tablename__ = "subject_owner_assignments"
    __table_args__ = (UniqueConstraint("subject_id", name="uq_one_owner_per_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    owner_teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
