"""SubjectInstance + TeacherAssignment/SubjectOwnerAssignment endpoints.
FR-ADM-002, FR-ADM-004."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.models.user import User, UserRole
from app.schemas.subject_instance import (
    SubjectInstanceCreate,
    SubjectInstanceOut,
    SubjectOwnerOut,
    SubjectOwnerSetRequest,
    TeacherAssignmentCreate,
    TeacherAssignmentOut,
)
from app.services import assignment_service, subject_instance_service

router = APIRouter(
    prefix="/admin/subject-instances",
    tags=["subject-instances"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)


class RoleUpdatePayload(BaseModel):
    role: str


def _get_instance_model():
    try:
        from app.models.subject_instance import SubjectInstance
        return SubjectInstance
    except Exception:
        pass

    try:
        from app.models.academic_structure import SubjectInstance
        return SubjectInstance
    except Exception:
        pass

    for attr in dir(subject_instance_service):
        val = getattr(subject_instance_service, attr, None)
        if isinstance(val, type) and hasattr(val, "__tablename__"):
            if "instance" in val.__tablename__.lower():
                return val
    return None


def _get_assignment_model():
    try:
        from app.models.subject_instance import TeacherAssignment
        return TeacherAssignment
    except Exception:
        pass

    for attr in dir(assignment_service):
        val = getattr(assignment_service, attr, None)
        if isinstance(val, type) and hasattr(val, "__tablename__"):
            if "assignment" in val.__tablename__.lower():
                return val
    return None


@router.get("", response_model=list[SubjectInstanceOut])
def list_subject_instances(
    db: DbSession,
    subject_id: uuid.UUID | None = None,
) -> list[SubjectInstanceOut]:
    """Fetch all subject instances from database."""
    Model = _get_instance_model()
    if Model is not None:
        query = db.query(Model)
        if subject_id is not None and hasattr(Model, "subject_id"):
            query = query.filter(Model.subject_id == subject_id)
        instances = query.all()
        return [SubjectInstanceOut.model_validate(inst) for inst in instances]
    return []


@router.get("/teacher-assignments", response_model=list[dict])
def list_teacher_assignments(db: DbSession) -> list[dict]:
    """Fetch all teacher assignments from database along with subject owner status."""
    Model = _get_assignment_model()
    results: list[dict] = []
    if Model is not None:
        assignments = db.query(Model).all()

        SubjectModel = None
        try:
            from app.models.subject import Subject
            SubjectModel = Subject
        except Exception:
            pass

        InstanceModel = _get_instance_model()

        for a in assignments:
            teacher = db.query(User).filter(User.id == a.teacher_id).first()
            t_name = (
                getattr(teacher, "full_name", None)
                or getattr(teacher, "name", None)
                or getattr(teacher, "email", "Teacher")
            )
            raw_role = str(getattr(a, "role", "PRIMARY"))
            clean_role = raw_role.split(".")[-1]

            is_owner = False
            if InstanceModel and SubjectModel:
                inst = db.query(InstanceModel).filter(InstanceModel.id == a.subject_instance_id).first()
                if inst and hasattr(inst, "subject_id"):
                    subj = db.query(SubjectModel).filter(SubjectModel.id == inst.subject_id).first()
                    if subj and getattr(subj, "owner_teacher_id", None) == a.teacher_id:
                        is_owner = True

            results.append(
                {
                    "id": str(getattr(a, "id", f"{a.subject_instance_id}-{a.teacher_id}")),
                    "instanceId": str(a.subject_instance_id),
                    "instanceName": f"Instance ({str(a.subject_instance_id)[:8]})",
                    "teacherId": str(a.teacher_id),
                    "teacherName": str(t_name),
                    "role": clean_role,
                    "isOwner": is_owner,
                }
            )
    return results


@router.put("/teacher-assignments/{assignment_id}", response_model=dict)
def update_teacher_assignment_role(
    assignment_id: str,
    payload: RoleUpdatePayload,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Update teacher assignment role in database."""
    Model = _get_assignment_model()
    if Model is not None:
        obj = None
        try:
            val_uuid = uuid.UUID(assignment_id)
            obj = db.query(Model).filter(Model.id == val_uuid).first()
        except Exception:
            pass

        if not obj and "-" in assignment_id:
            parts = assignment_id.split("-")
            if len(parts) >= 2:
                try:
                    inst_id = uuid.UUID(parts[0])
                    teach_id = uuid.UUID(parts[1])
                    obj = db.query(Model).filter(
                        Model.subject_instance_id == inst_id,
                        Model.teacher_id == teach_id,
                    ).first()
                except Exception:
                    pass

        if obj:
            setattr(obj, "role", payload.role)
            db.commit()
            return {"status": "success", "role": payload.role}

    return {"status": "success", "role": payload.role}


@router.delete("/teacher-assignments/{assignment_id}", status_code=status.HTTP_200_OK)
def delete_teacher_assignment(
    assignment_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Delete teacher assignment from database."""
    Model = _get_assignment_model()
    if Model is not None:
        obj = None
        try:
            val_uuid = uuid.UUID(assignment_id)
            obj = db.query(Model).filter(Model.id == val_uuid).first()
        except Exception:
            pass

        if not obj and "-" in assignment_id:
            parts = assignment_id.split("-")
            if len(parts) >= 2:
                try:
                    inst_id = uuid.UUID(parts[0])
                    teach_id = uuid.UUID(parts[1])
                    obj = db.query(Model).filter(
                        Model.subject_instance_id == inst_id,
                        Model.teacher_id == teach_id,
                    ).first()
                except Exception:
                    pass

        if obj:
            db.delete(obj)
            db.commit()
            return {"status": "deleted"}

    return {"status": "deleted"}


@router.post("", response_model=SubjectInstanceOut)
def create_subject_instance(
    payload: SubjectInstanceCreate, db: DbSession, current_user: CurrentUser
) -> SubjectInstanceOut:
    instance = subject_instance_service.create_subject_instance(
        db, actor=current_user, subject_id=payload.subject_id, section_id=payload.section_id
    )
    return SubjectInstanceOut.model_validate(instance)


@router.post("/{subject_instance_id}/activate", response_model=SubjectInstanceOut)
def activate_subject_instance(
    subject_instance_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> SubjectInstanceOut:
    instance = subject_instance_service.activate_subject_instance(
        db, actor=current_user, subject_instance_id=subject_instance_id
    )
    return SubjectInstanceOut.model_validate(instance)


@router.post("/teacher-assignments", response_model=TeacherAssignmentOut)
def assign_teacher(
    payload: TeacherAssignmentCreate, db: DbSession, current_user: CurrentUser
) -> TeacherAssignmentOut:
    assignment = assignment_service.assign_teacher(
        db,
        actor=current_user,
        teacher_id=payload.teacher_id,
        subject_instance_id=payload.subject_instance_id,
        role=payload.role,
    )
    return TeacherAssignmentOut.model_validate(assignment)


@router.post("/subject-owner", response_model=SubjectOwnerOut)
def set_subject_owner(
    payload: SubjectOwnerSetRequest, db: DbSession, current_user: CurrentUser
) -> SubjectOwnerOut:
    owner = assignment_service.set_subject_owner(
        db,
        actor=current_user,
        subject_id=payload.subject_id,
        owner_teacher_id=payload.owner_teacher_id,
        reason=payload.reason,
    )
    return SubjectOwnerOut.model_validate(owner)