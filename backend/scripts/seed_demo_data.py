"""Seeds one Institute -> one Department -> one Program -> one Batch ->
two Sections, a handful of Subjects (including one elective group and one
LAB-type Subject), Teacher/Student accounts, and calendar/timetable rows.

Idempotent: re-running looks up existing rows by their unique
codes/emails instead of inserting duplicates (verified by
`tests/unit/test_seed_data.py::test_seed_is_idempotent_and_consistent`).

Run with: `python -m scripts.seed_demo_data` from `backend/`.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.academic_structure import Batch, Department, Institute, Program, Section, Semester
from app.models.calendar import AcademicCalendar
from app.models.subject import ElectiveGroup, Subject, SubjectType
from app.models.subject_instance import (
    SubjectInstance,
    SubjectInstanceStatus,
    TeacherAssignment,
    TeacherAssignmentRole,
)
from app.models.user import User, UserRole
from app.services import calendar_service, subject_service


def _get_or_create_institute(db: Session) -> Institute:
    institute = db.scalar(select(Institute).where(Institute.name == "UniAdapt Institute of Technology"))
    if institute is None:
        institute = Institute(name="UniAdapt Institute of Technology", timezone="Asia/Kolkata")
        db.add(institute)
        db.flush()
    return institute


def _get_or_create_user(db: Session, *, email: str, full_name: str, role: UserRole) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            password_hash=hash_password("ChangeMe123!"),
            is_active=True,
            token_version=0,
            activated_at=dt.datetime.now(dt.UTC),
        )
        db.add(user)
        db.flush()
    return user


def seed(db: Session) -> None:
    institute = _get_or_create_institute(db)

    department = db.scalar(
        select(Department).where(Department.institute_id == institute.id, Department.code == "CSE")
    )
    if department is None:
        department = Department(institute_id=institute.id, code="CSE", name="Computer Science & Engineering")
        db.add(department)
        db.flush()

    program = db.scalar(
        select(Program).where(Program.department_id == department.id, Program.code == "BTECH-CSE")
    )
    if program is None:
        program = Program(
            department_id=department.id, code="BTECH-CSE", name="B.Tech CSE", duration_semesters=8
        )
        db.add(program)
        db.flush()

    batch = db.scalar(select(Batch).where(Batch.program_id == program.id, Batch.start_year == 2024))
    if batch is None:
        batch = Batch(program_id=program.id, start_year=2024, end_year=2028)
        db.add(batch)
        db.flush()

    semester = db.scalar(select(Semester).where(Semester.batch_id == batch.id, Semester.number == 3))
    if semester is None:
        semester = Semester(
            batch_id=batch.id, number=3, start_date=dt.date(2025, 8, 1), end_date=dt.date(2025, 12, 20)
        )
        db.add(semester)
        db.flush()

    sections = {}
    for name, capacity in (("A", 60), ("B", 60)):
        section = db.scalar(select(Section).where(Section.semester_id == semester.id, Section.name == name))
        if section is None:
            section = Section(semester_id=semester.id, name=name, capacity=capacity)
            db.add(section)
            db.flush()
        sections[name] = section

    teacher = _get_or_create_user(
        db, email="teacher.demo@example.com", full_name="Demo Teacher", role=UserRole.TEACHER
    )
    admin_user = _get_or_create_user(
        db, email="admin.demo@example.com", full_name="Demo Admin", role=UserRole.ADMIN
    )
    _get_or_create_user(
        db, email="student.demo@example.com", full_name="Demo Student", role=UserRole.STUDENT
    )

    elective_group = db.scalar(
        select(ElectiveGroup).where(
            ElectiveGroup.program_id == program.id,
            ElectiveGroup.semester_no == 3,
            ElectiveGroup.name == "Open Elective 1",
        )
    )
    if elective_group is None:
        elective_group = subject_service.create_elective_group(
            db, actor=admin_user, program_id=program.id, semester_no=3, name="Open Elective 1", required=True
        )

    core_subject = db.scalar(
        select(Subject).where(
            Subject.program_id == program.id, Subject.semester_no == 3, Subject.code == "CS301"
        )
    )
    if core_subject is None:
        core_subject = subject_service.create_subject(
            db,
            actor=admin_user,
            program_id=program.id,
            semester_no=3,
            code="CS301",
            name="Data Structures",
            credits=4,
            type_=SubjectType.CORE,
            elective_group_id=None,
        )
        subject_service.set_units(
            db,
            actor=admin_user,
            subject_id=core_subject.id,
            units=[
                {"order_index": 1, "name": "Arrays & Linked Lists", "weightage": 25},
                {"order_index": 2, "name": "Stacks & Queues", "weightage": 25},
                {"order_index": 3, "name": "Trees", "weightage": 25},
                {"order_index": 4, "name": "Graphs", "weightage": 25},
            ],
        )

    lab_subject = db.scalar(
        select(Subject).where(
            Subject.program_id == program.id, Subject.semester_no == 3, Subject.code == "CS301L"
        )
    )
    if lab_subject is None:
        lab_subject = subject_service.create_subject(
            db,
            actor=admin_user,
            program_id=program.id,
            semester_no=3,
            code="CS301L",
            name="Data Structures Lab",
            credits=1,
            type_=SubjectType.LAB,
            elective_group_id=None,
        )

    elective_subject = db.scalar(
        select(Subject).where(
            Subject.program_id == program.id, Subject.semester_no == 3, Subject.code == "OE301"
        )
    )
    if elective_subject is None:
        elective_subject = subject_service.create_subject(
            db,
            actor=admin_user,
            program_id=program.id,
            semester_no=3,
            code="OE301",
            name="Intro to Robotics",
            credits=3,
            type_=SubjectType.ELECTIVE,
            elective_group_id=elective_group.id,
        )

    for subject in (core_subject, lab_subject, elective_subject):
        instance = db.scalar(
            select(SubjectInstance).where(
                SubjectInstance.subject_id == subject.id, SubjectInstance.section_id == sections["A"].id
            )
        )
        if instance is None:
            instance = SubjectInstance(
                subject_id=subject.id, section_id=sections["A"].id, status=SubjectInstanceStatus.DRAFT
            )
            db.add(instance)
            db.flush()
        has_assignment = db.scalar(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == teacher.id,
                TeacherAssignment.subject_instance_id == instance.id,
            )
        )
        if has_assignment is None:
            db.add(
                TeacherAssignment(
                    teacher_id=teacher.id, subject_instance_id=instance.id, role=TeacherAssignmentRole.PRIMARY
                )
            )
            db.flush()
        instance.status = SubjectInstanceStatus.ACTIVE

    existing_calendar = db.scalar(select(AcademicCalendar).where(AcademicCalendar.semester_id == semester.id))
    if existing_calendar is None:
        calendar_service.create_academic_calendar(
            db,
            actor=admin_user,
            semester_id=semester.id,
            holidays=["2025-10-02"],
            ia_window=(dt.date(2025, 9, 15), dt.date(2025, 9, 25)),
            practical_window=(dt.date(2025, 11, 1), dt.date(2025, 11, 15)),
            university_exam_window=(dt.date(2025, 12, 1), dt.date(2025, 12, 18)),
        )

    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
