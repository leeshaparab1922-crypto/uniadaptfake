"""Demo roles for Phase 2 (NFR-TST-002, Section 43 demo): on the first seeded Subject, the demo
Admin assigns the Phase 1 demo Teacher as Subject Owner (FR-ADM-002, ADR-0003) and adds a second
demo Teacher as a CO Teacher on the same SubjectInstance, both through the real Phase 1 services
(audited). The Phase 1 seed itself is left unchanged.

Prerequisite: `python -m scripts.seed_demo_data`. Idempotent.
Run with: `python -m scripts.seed_phase2_demo_roles` from `backend/`.
Demo logins (development only): teacher.demo@example.com (Owner), co.teacher.demo@example.com (CO),
password ChangeMe123! like the Phase 1 demo accounts.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.subject import Subject
from app.models.subject_instance import (
    SubjectInstance,
    SubjectOwnerAssignment,
    TeacherAssignment,
    TeacherAssignmentRole,
)
from app.models.user import User, UserRole
from app.services import assignment_service

OWNER_EMAIL = "teacher.demo@example.com"
CO_EMAIL = "co.teacher.demo@example.com"
ADMIN_EMAIL = "admin.demo@example.com"
DEMO_PASSWORD = "ChangeMe123!"  # development demo account, same as the Phase 1 seed


def main() -> None:
    with SessionLocal() as db:
        subject = db.scalars(select(Subject).order_by(Subject.code)).first()
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        owner = db.scalar(select(User).where(User.email == OWNER_EMAIL))
        if subject is None or admin is None or owner is None:
            raise SystemExit("Run `python -m scripts.seed_demo_data` first.")
        instance = db.scalar(select(SubjectInstance).where(SubjectInstance.subject_id == subject.id))
        if instance is None:
            raise SystemExit("The demo Subject has no SubjectInstance; run the Phase 1 seed first.")

        if (
            db.scalar(select(SubjectOwnerAssignment).where(SubjectOwnerAssignment.subject_id == subject.id))
            is None
        ):
            assignment_service.set_subject_owner(
                db, actor=admin, subject_id=subject.id, owner_teacher_id=owner.id, reason="Phase 2 demo"
            )
            print(f"Subject Owner of {subject.code}: {OWNER_EMAIL}")

        co = db.scalar(select(User).where(User.email == CO_EMAIL))
        if co is None:
            co = User(
                email=CO_EMAIL,
                full_name="Demo CO Teacher",
                role=UserRole.TEACHER,
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
                token_version=0,
                activated_at=dt.datetime.now(dt.UTC),
            )
            db.add(co)
            db.flush()
        has_co = db.scalar(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == co.id, TeacherAssignment.subject_instance_id == instance.id
            )
        )
        if has_co is None:
            assignment_service.assign_teacher(
                db,
                actor=admin,
                teacher_id=co.id,
                subject_instance_id=instance.id,
                role=TeacherAssignmentRole.CO,
            )
            print(f"CO Teacher on {subject.code}: {CO_EMAIL}")
        db.commit()
        print("Phase 2 demo roles ready.")


if __name__ == "__main__":
    main()
