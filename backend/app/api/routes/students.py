"""Student CSV import endpoint. FR-ADM-005."""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.models.user import UserRole
from app.schemas.student import ImportRowErrorOut, ImportSummaryOut
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
