"""Builds a small academic world (one Subject with 3 Units, owner + CO + unassigned
Teachers) through the Phase 1 service layer, for Phase 2 tests on PostgreSQL."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.subject import Subject, SubjectType, Unit
from app.models.subject_instance import SubjectInstance, TeacherAssignmentRole
from app.models.user import User, UserRole
from app.services import academic_structure_service as academic_service
from app.services import assignment_service, subject_instance_service, subject_service

PASSWORD = "Secret123!"


@dataclass
class World:
    admin: User
    owner: User  # PRIMARY teacher and Subject Owner
    co: User  # CO teacher on the same instance
    outsider: User  # TEACHER with no assignment on the Subject
    subject: Subject
    units: list[Unit]
    instance: SubjectInstance
    program_id: uuid.UUID


def _user(db: Session, email: str, role: UserRole) -> User:
    user = User(
        email=email,
        full_name=email.split("@")[0],
        password_hash=hash_password(PASSWORD),
        role=role,
        is_active=True,
        token_version=0,
    )
    db.add(user)
    db.flush()
    return user


def build_world(db: Session, *, tag: str | None = None) -> World:
    tag = tag or uuid.uuid4().hex[:6]
    admin = _user(db, f"admin-{tag}@example.com", UserRole.ADMIN)
    owner = _user(db, f"owner-{tag}@example.com", UserRole.TEACHER)
    co = _user(db, f"co-{tag}@example.com", UserRole.TEACHER)
    outsider = _user(db, f"outsider-{tag}@example.com", UserRole.TEACHER)
    db.commit()

    institute = academic_service.create_institute(
        db, actor=admin, name=f"Inst {tag}", timezone="Asia/Kolkata"
    )
    dept = academic_service.create_department(
        db, actor=admin, institute_id=institute.id, code="CSE", name="CSE"
    )
    program = academic_service.create_program(
        db, actor=admin, department_id=dept.id, code="BT", name="B.Tech", duration_semesters=8
    )
    batch = academic_service.create_batch(
        db, actor=admin, program_id=program.id, start_year=2024, end_year=2028
    )
    semester = academic_service.create_semester(
        db,
        actor=admin,
        batch_id=batch.id,
        number=3,
        start_date=dt.date(2025, 8, 1),
        end_date=dt.date(2025, 12, 1),
    )
    section = academic_service.create_section(db, actor=admin, semester_id=semester.id, name="A", capacity=60)
    subject = subject_service.create_subject(
        db,
        actor=admin,
        program_id=program.id,
        semester_no=3,
        code="CS301",
        name="Data Structures",
        credits=4,
        type_=SubjectType.CORE,
        elective_group_id=None,
    )
    units = subject_service.set_units(
        db,
        actor=admin,
        subject_id=subject.id,
        units=[
            {"order_index": 1, "name": "Basics", "weightage": 34},
            {"order_index": 2, "name": "Trees", "weightage": 33},
            {"order_index": 3, "name": "Graphs", "weightage": 33},
        ],
    )
    instance = subject_instance_service.create_subject_instance(
        db, actor=admin, subject_id=subject.id, section_id=section.id
    )
    assignment_service.assign_teacher(
        db,
        actor=admin,
        teacher_id=owner.id,
        subject_instance_id=instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )
    assignment_service.assign_teacher(
        db, actor=admin, teacher_id=co.id, subject_instance_id=instance.id, role=TeacherAssignmentRole.CO
    )
    assignment_service.set_subject_owner(db, actor=admin, subject_id=subject.id, owner_teacher_id=owner.id)
    db.commit()
    return World(admin, owner, co, outsider, subject, list(units), instance, program.id)


def login(client, user: User) -> dict[str, str]:
    """Logs `user` in on `client`; returns the CSRF header for mutating requests."""
    response = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}
