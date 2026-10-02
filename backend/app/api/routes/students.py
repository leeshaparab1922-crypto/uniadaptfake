"""Student CSV import and read-only listing endpoints. FR-ADM-005."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.models.student import Student
from app.models.user import User, UserRole
from app.schemas.student import (
    ImportRowErrorOut,
    ImportSummaryOut,
    StudentListItemOut,
    StudentListOut,
)
from app.services import student_import_service

router = APIRouter(
    prefix="/admin/students",
    tags=["students"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # NFR-SEC uploads rule: 25MB limit.


@router.post("/import", response_model=ImportSummaryOut)
async def import_students(file: UploadFile, db: DbSession, current_user: CurrentUser) -> ImportSummaryOut:
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    student_import_service.validate_upload(
        filename=file.filename,
        content_type=file.content_type,
        size=len(raw),
        max_bytes=MAX_UPLOAD_BYTES,
    )
    csv_text = raw.decode("utf-8-sig")
    summary = student_import_service.import_students_csv(db, actor=current_user, csv_text=csv_text)
    return ImportSummaryOut(
        created=summary.created,
        errors=[ImportRowErrorOut(row_number=e.row_number, reason=e.reason) for e in summary.errors],
    )


@router.get("", response_model=StudentListOut)
def list_students(
    db: DbSession,
    department_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    current_semester_no: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> StudentListOut:
    """Read-only Admin view of students (e.g. to verify a CSV import)."""
    conditions = []
    if department_id is not None:
        conditions.append(Student.department_id == department_id)
    if batch_id is not None:
        conditions.append(Student.batch_id == batch_id)
    if section_id is not None:
        conditions.append(Student.section_id == section_id)
    if current_semester_no is not None:
        conditions.append(Student.current_semester_no == current_semester_no)

    total = db.scalar(select(func.count()).select_from(Student).where(*conditions)) or 0
    rows = db.execute(
        select(Student, User.email, User.full_name)
        .join(User, User.id == Student.user_id)
        .where(*conditions)
        .order_by(Student.roll_number)
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        StudentListItemOut(
            id=s.id,
            user_id=s.user_id,
            roll_number=s.roll_number,
            department_id=s.department_id,
            batch_id=s.batch_id,
            section_id=s.section_id,
            current_semester_no=s.current_semester_no,
            email=email,
            full_name=full_name,
        )
        for s, email, full_name in rows
    ]
    return StudentListOut(items=items, total=total, limit=limit, offset=offset)
