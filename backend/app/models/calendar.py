"""Academic calendar and Section timetable. FR-ADM-007.

ADR-0007: `SectionTimetableSlot.type` allows exactly CLASS and LAB - the
only two the SRS names.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, time

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Time,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SlotType(str, enum.Enum):
    CLASS = "CLASS"
    LAB = "LAB"


class AcademicCalendar(Base, TimestampMixin):
    __tablename__ = "academic_calendars"
    __table_args__ = (
        UniqueConstraint(
            "semester_id", "version", name="uq_calendar_version_per_semester"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    semester_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("semesters.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    holidays: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ia_window_start: Mapped[date] = mapped_column(Date, nullable=False)
    ia_window_end: Mapped[date] = mapped_column(Date, nullable=False)
    practical_window_start: Mapped[date] = mapped_column(Date, nullable=False)
    practical_window_end: Mapped[date] = mapped_column(Date, nullable=False)
    university_exam_window_start: Mapped[date] = mapped_column(Date, nullable=False)
    university_exam_window_end: Mapped[date] = mapped_column(Date, nullable=False)


class SectionTimetableSlot(Base, TimestampMixin):
    __tablename__ = "section_timetable_slots"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="ck_slot_start_before_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sections.id", ondelete="RESTRICT"), nullable=False
    )
    subject_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subject_instances.id", ondelete="RESTRICT"), nullable=True
    )
    day_of_week: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 0=Monday .. 6=Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    type: Mapped[SlotType] = mapped_column(
        SAEnum(
            SlotType,
            name="slot_type",
            native_enum=False,
            create_constraint=True,
            length=8,
        ),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
