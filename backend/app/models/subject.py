"""Subject catalogue: Subject, ElectiveGroup, Unit. FR-ADM-003.

Unit weightage per-row range is a DB CHECK; the cross-row "sum to exactly
100" invariant is enforced in `subject_service` under a Subject row lock
(ADR-0002), not as a database constraint.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SubjectType(str, enum.Enum):
    CORE = "CORE"
    ELECTIVE = "ELECTIVE"
    LAB = "LAB"  # BUS-042: LAB subjects are excluded from adaptive planning (enforced Phase 7/12).


class ElectiveGroup(Base, TimestampMixin):
    __tablename__ = "elective_groups"
    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "semester_no",
            "name",
            name="uq_elective_group_per_program_semester",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False
    )
    semester_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "semester_no",
            "code",
            name="uq_subject_code_per_program_semester",
        ),
        CheckConstraint("credits >= 0", name="ck_subject_credits_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False
    )
    semester_no: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[SubjectType] = mapped_column(
        SAEnum(
            SubjectType,
            name="subject_type",
            native_enum=False,
            create_constraint=True,
            length=16,
        ),
        nullable=False,
    )
    elective_group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("elective_groups.id", ondelete="RESTRICT"), nullable=True
    )


class Unit(Base, TimestampMixin):
    __tablename__ = "units"
    __table_args__ = (
        CheckConstraint(
            "weightage >= 0 AND weightage <= 100", name="ck_unit_weightage_range"
        ),
        UniqueConstraint("subject_id", "order_index", name="uq_unit_order_per_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weightage: Mapped[int] = mapped_column(Integer, nullable=False)
