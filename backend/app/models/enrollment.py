"""Enrollment (read-only to Students - BUS-001) and StudentPlacementHistory
(promotion/transfer history - BUS-049). FR-ADM-006, FR-STU-001.

`StudentPreference` (SRS Section 31.1) is deliberately NOT modeled here -
deferred to Phase 7 per ADR-0004.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from app.db.base import Base, TimestampMixin


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"
    __table_args__ = (
        # Partial unique index: a Student may have at most one ACTIVE
        # Enrollment per SubjectInstance at a time. Closed/history rows are
        # preserved (BUS-049) and excluded from this constraint.
        Index(
            "uq_enrollment_active_student_instance",
            "student_id",
            "subject_instance_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
            sqlite_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    subject_instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_instances.id", ondelete="RESTRICT"), nullable=False
    )
    elective_group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("elective_groups.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        SAEnum(
            EnrollmentStatus,
            name="enrollment_status",
            native_enum=False,
            create_constraint=True,
            length=8,
        ),
        nullable=False,
        default=EnrollmentStatus.ACTIVE,
    )
    auto_allocated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class StudentPlacementHistory(Base, TimestampMixin):
    __tablename__ = "student_placement_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    from_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("batches.id", ondelete="RESTRICT"), nullable=True
    )
    to_batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False
    )
    from_semester_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_semester_no: Mapped[int] = mapped_column(Integer, nullable=False)
    from_section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="RESTRICT"), nullable=True
    )
    to_section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sections.id", ondelete="RESTRICT"), nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    operation_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
