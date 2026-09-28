"""Initial Foundation schema (Phase 1: FR-AUTH-001..004, FR-ADM-001..007,
FR-STU-001).

Revision ID: 0001
Revises:
Create Date: 2026-09-27

Enums are stored as VARCHAR + a named CHECK constraint (ADR-0009), not
native Postgres ENUM types, via `sa.Enum(..., native_enum=False,
create_constraint=True)`. `StudentPreference` is intentionally not created
here - deferred to Phase 7 (ADR-0004).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "ADMIN",
                "TEACHER",
                "STUDENT",
                name="user_role",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reset_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "invitation_tokens",
        _uuid_pk(),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("token_hash", name="uq_invitation_tokens_token_hash"),
    )
    op.create_index("ix_invitation_tokens_user_id", "invitation_tokens", ["user_id"])

    op.create_table(
        "password_reset_tokens",
        _uuid_pk(),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "audit_logs",
        _uuid_pk(),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "institutes",
        _uuid_pk(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        *_timestamps(),
    )

    op.create_table(
        "departments",
        _uuid_pk(),
        sa.Column(
            "institute_id", sa.Uuid(), sa.ForeignKey("institutes.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("institute_id", "code", name="uq_department_code_per_institute"),
    )

    op.create_table(
        "programs",
        _uuid_pk(),
        sa.Column(
            "department_id", sa.Uuid(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("duration_semesters", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("department_id", "code", name="uq_program_code_per_department"),
    )

    op.create_table(
        "batches",
        _uuid_pk(),
        sa.Column("program_id", sa.Uuid(), sa.ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("program_id", "start_year", name="uq_batch_start_year_per_program"),
        sa.CheckConstraint("start_year <= end_year", name="ck_batch_start_before_end"),
    )

    op.create_table(
        "semesters",
        _uuid_pk(),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("batch_id", "number", name="uq_semester_number_per_batch"),
        sa.CheckConstraint("start_date < end_date", name="ck_semester_start_before_end"),
    )

    op.create_table(
        "sections",
        _uuid_pk(),
        sa.Column(
            "semester_id", sa.Uuid(), sa.ForeignKey("semesters.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("name", sa.String(20), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("semester_id", "name", name="uq_section_name_per_semester"),
        sa.CheckConstraint("capacity > 0", name="ck_section_capacity_positive"),
    )

    op.create_table(
        "academic_calendars",
        _uuid_pk(),
        sa.Column(
            "semester_id", sa.Uuid(), sa.ForeignKey("semesters.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("holidays", sa.JSON(), nullable=False),
        sa.Column("ia_window_start", sa.Date(), nullable=False),
        sa.Column("ia_window_end", sa.Date(), nullable=False),
        sa.Column("practical_window_start", sa.Date(), nullable=False),
        sa.Column("practical_window_end", sa.Date(), nullable=False),
        sa.Column("university_exam_window_start", sa.Date(), nullable=False),
        sa.Column("university_exam_window_end", sa.Date(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("semester_id", "version", name="uq_calendar_version_per_semester"),
    )

    op.create_table(
        "elective_groups",
        _uuid_pk(),
        sa.Column("program_id", sa.Uuid(), sa.ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("semester_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint(
            "program_id", "semester_no", "name", name="uq_elective_group_per_program_semester"
        ),
    )

    op.create_table(
        "subjects",
        _uuid_pk(),
        sa.Column("program_id", sa.Uuid(), sa.ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("semester_no", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "CORE",
                "ELECTIVE",
                "LAB",
                name="subject_type",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "elective_group_id",
            sa.Uuid(),
            sa.ForeignKey("elective_groups.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        *_timestamps(),
        sa.UniqueConstraint("program_id", "semester_no", "code", name="uq_subject_code_per_program_semester"),
        sa.CheckConstraint("credits >= 0", name="ck_subject_credits_nonnegative"),
    )

    op.create_table(
        "units",
        _uuid_pk(),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("weightage", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("subject_id", "order_index", name="uq_unit_order_per_subject"),
        sa.CheckConstraint("weightage >= 0 AND weightage <= 100", name="ck_unit_weightage_range"),
    )

    op.create_table(
        "subject_instances",
        _uuid_pk(),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_id", sa.Uuid(), sa.ForeignKey("sections.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("exam_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "ACTIVE",
                name="subject_instance_status",
                native_enum=False,
                create_constraint=True,
                length=8,
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        *_timestamps(),
        sa.UniqueConstraint("subject_id", "section_id", name="uq_subject_instance_per_section"),
    )

    op.create_table(
        "teacher_assignments",
        _uuid_pk(),
        sa.Column("teacher_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "subject_instance_id",
            sa.Uuid(),
            sa.ForeignKey("subject_instances.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(
                "PRIMARY",
                "CO",
                name="teacher_assignment_role",
                native_enum=False,
                create_constraint=True,
                length=8,
            ),
            nullable=False,
        ),
        *_timestamps(),
        sa.UniqueConstraint("teacher_id", "subject_instance_id", name="uq_teacher_per_instance"),
    )

    op.create_table(
        "subject_owner_assignments",
        _uuid_pk(),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "owner_teacher_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        *_timestamps(),
        sa.UniqueConstraint("subject_id", name="uq_one_owner_per_subject"),
    )

    op.create_table(
        "section_timetable_slots",
        _uuid_pk(),
        sa.Column("section_id", sa.Uuid(), sa.ForeignKey("sections.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "subject_instance_id",
            sa.Uuid(),
            sa.ForeignKey("subject_instances.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("CLASS", "LAB", name="slot_type", native_enum=False, create_constraint=True, length=8),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("start_time < end_time", name="ck_slot_start_before_end"),
    )

    op.create_table(
        "students",
        _uuid_pk(),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("roll_number", sa.String(50), nullable=False),
        sa.Column(
            "department_id", sa.Uuid(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_id", sa.Uuid(), sa.ForeignKey("sections.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("current_semester_no", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("user_id", name="uq_students_user_id"),
        sa.UniqueConstraint("roll_number", name="uq_students_roll_number"),
    )

    op.create_table(
        "enrollments",
        _uuid_pk(),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "subject_instance_id",
            sa.Uuid(),
            sa.ForeignKey("subject_instances.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "elective_group_id",
            sa.Uuid(),
            sa.ForeignKey("elective_groups.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "CLOSED",
                name="enrollment_status",
                native_enum=False,
                create_constraint=True,
                length=8,
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("auto_allocated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "uq_enrollment_active_student_instance",
        "enrollments",
        ["student_id", "subject_instance_id"],
        unique=True,
        sqlite_where=sa.text("status = 'ACTIVE'"),
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "student_placement_history",
        _uuid_pk(),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "from_batch_id", sa.Uuid(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("to_batch_id", sa.Uuid(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_semester_no", sa.Integer(), nullable=True),
        sa.Column("to_semester_no", sa.Integer(), nullable=False),
        sa.Column(
            "from_section_id", sa.Uuid(), sa.ForeignKey("sections.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column(
            "to_section_id", sa.Uuid(), sa.ForeignKey("sections.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_student_placement_history_operation_id", "student_placement_history", ["operation_id"]
    )


def downgrade() -> None:
    op.drop_table("student_placement_history")
    op.drop_index("uq_enrollment_active_student_instance", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_table("students")
    op.drop_table("section_timetable_slots")
    op.drop_table("subject_owner_assignments")
    op.drop_table("teacher_assignments")
    op.drop_table("subject_instances")
    op.drop_table("units")
    op.drop_table("subjects")
    op.drop_table("elective_groups")
    op.drop_table("academic_calendars")
    op.drop_table("sections")
    op.drop_table("semesters")
    op.drop_table("batches")
    op.drop_table("programs")
    op.drop_table("departments")
    op.drop_table("institutes")
    op.drop_table("audit_logs")
    op.drop_table("password_reset_tokens")
    op.drop_table("invitation_tokens")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
