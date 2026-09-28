"""Institute/Department/Program/Batch/Semester/Section endpoints. FR-ADM-001."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.models.user import UserRole
from app.schemas.academic_structure import (
    BatchCreate,
    BatchOut,
    DepartmentCreate,
    DepartmentOut,
    InstituteCreate,
    InstituteOut,
    ProgramCreate,
    ProgramOut,
    SectionCreate,
    SectionOut,
    SemesterCreate,
    SemesterOut,
)
from app.services import academic_structure_service as service

router = APIRouter(
    prefix="/admin/academic-structure",
    tags=["academic-structure"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)


@router.post("/institutes", response_model=InstituteOut)
def create_institute(payload: InstituteCreate, db: DbSession, current_user: CurrentUser) -> InstituteOut:
    institute = service.create_institute(db, actor=current_user, name=payload.name, timezone=payload.timezone)
    return InstituteOut.model_validate(institute)


@router.post("/departments", response_model=DepartmentOut)
def create_department(payload: DepartmentCreate, db: DbSession, current_user: CurrentUser) -> DepartmentOut:
    dept = service.create_department(
        db,
        actor=current_user,
        institute_id=payload.institute_id,
        code=payload.code,
        name=payload.name,
    )
    return DepartmentOut.model_validate(dept)


@router.post("/programs", response_model=ProgramOut)
def create_program(payload: ProgramCreate, db: DbSession, current_user: CurrentUser) -> ProgramOut:
    program = service.create_program(
        db,
        actor=current_user,
        department_id=payload.department_id,
        code=payload.code,
        name=payload.name,
        duration_semesters=payload.duration_semesters,
    )
    return ProgramOut.model_validate(program)


@router.post("/batches", response_model=BatchOut)
def create_batch(payload: BatchCreate, db: DbSession, current_user: CurrentUser) -> BatchOut:
    batch = service.create_batch(
        db,
        actor=current_user,
        program_id=payload.program_id,
        start_year=payload.start_year,
        end_year=payload.end_year,
    )
    return BatchOut.model_validate(batch)


@router.post("/semesters", response_model=SemesterOut)
def create_semester(payload: SemesterCreate, db: DbSession, current_user: CurrentUser) -> SemesterOut:
    semester = service.create_semester(
        db,
        actor=current_user,
        batch_id=payload.batch_id,
        number=payload.number,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    return SemesterOut.model_validate(semester)


@router.post("/sections", response_model=SectionOut)
def create_section(payload: SectionCreate, db: DbSession, current_user: CurrentUser) -> SectionOut:
    section = service.create_section(
        db,
        actor=current_user,
        semester_id=payload.semester_id,
        name=payload.name,
        capacity=payload.capacity,
    )
    return SectionOut.model_validate(section)
