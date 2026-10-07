"""Subject/Unit/ElectiveGroup & Teacher endpoints. FR-ADM-003."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.schemas.subject import (
    ElectiveGroupCreate,
    ElectiveGroupOut,
    SubjectCreate,
    SubjectOut,
    UnitOut,
    UnitsSetRequest,
)
from app.services import subject_service as service

router = APIRouter(
    prefix="/admin/subjects",
    tags=["subjects"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)


class TeacherCreate(BaseModel):
    name: str
    email: EmailStr


class TeacherOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    class Config:
        from_attributes = True


def format_teacher_response(user: User) -> TeacherOut:
    """Safely extract display name irrespective of model column naming."""
    display_name = (
        getattr(user, "full_name", None)
        or getattr(user, "name", None)
        or getattr(user, "username", None)
        or user.email.split("@")[0]
    )
    return TeacherOut(id=user.id, name=str(display_name), email=user.email)


@router.get("", response_model=list[SubjectOut])
def list_subjects(
    db: DbSession,
    program_id: uuid.UUID | None = None,
) -> list[SubjectOut]:
    """Fetch all subjects or filter by program_id."""
    query = db.query(Subject)
    if program_id is not None:
        query = query.filter(Subject.program_id == program_id)
    subjects = query.all()
    return [SubjectOut.model_validate(s) for s in subjects]


@router.post("/elective-groups", response_model=ElectiveGroupOut)
def create_elective_group(
    payload: ElectiveGroupCreate, db: DbSession, current_user: CurrentUser
) -> ElectiveGroupOut:
    group = service.create_elective_group(
        db,
        actor=current_user,
        program_id=payload.program_id,
        semester_no=payload.semester_no,
        name=payload.name,
        required=payload.required,
    )
    return ElectiveGroupOut.model_validate(group)


@router.post("", response_model=SubjectOut)
def create_subject(payload: SubjectCreate, db: DbSession, current_user: CurrentUser) -> SubjectOut:
    subject = service.create_subject(
        db,
        actor=current_user,
        program_id=payload.program_id,
        semester_no=payload.semester_no,
        code=payload.code,
        name=payload.name,
        credits=payload.credits,
        type_=payload.type,
        elective_group_id=payload.elective_group_id,
    )
    return SubjectOut.model_validate(subject)


@router.put("/{subject_id}/units", response_model=list[UnitOut])
def set_units(
    subject_id: uuid.UUID, payload: UnitsSetRequest, db: DbSession, current_user: CurrentUser
) -> list[UnitOut]:
    units = service.set_units(
        db, actor=current_user, subject_id=subject_id, units=[u.model_dump() for u in payload.units]
    )
    return [UnitOut.model_validate(u) for u in units]


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> None:
    """Delete a subject by its UUID."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    db.delete(subject)
    db.commit()
    return None


@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(db: DbSession) -> list[TeacherOut]:
    """Fetch all users with role TEACHER."""
    teachers = db.query(User).filter(User.role == UserRole.TEACHER).all()
    return [format_teacher_response(t) for t in teachers]


@router.post("/teachers", response_model=TeacherOut)
def create_teacher(payload: TeacherCreate, db: DbSession, current_user: CurrentUser) -> TeacherOut:
    """Add a new teacher user dynamically supporting different User column names."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user_kwargs: dict = {
        "email": payload.email,
        "role": UserRole.TEACHER,
    }

    # Dynamically match full_name vs name
    if hasattr(User, "full_name"):
        user_kwargs["full_name"] = payload.name
    elif hasattr(User, "name"):
        user_kwargs["name"] = payload.name

    # Dynamically match password hash column
    dummy_hash = "seeded_default_hash"
    if hasattr(User, "hashed_password"):
        user_kwargs["hashed_password"] = dummy_hash
    elif hasattr(User, "password_hash"):
        user_kwargs["password_hash"] = dummy_hash

    # Handle active state if present
    if hasattr(User, "is_active"):
        user_kwargs["is_active"] = True

    new_teacher = User(**user_kwargs)
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return format_teacher_response(new_teacher)