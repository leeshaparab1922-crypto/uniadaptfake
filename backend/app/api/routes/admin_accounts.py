"""Admin account administration. FR-AUTH-003/004."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, csrf_protect, require_role
from app.core.errors import NotFoundError
from app.models.user import User, UserRole
from app.schemas.auth import (
    CreateAccountRequest,
    InvitationIssuedResponse,
    PasswordResetIssuedResponse,
    UserPublic,
)
from app.services import auth_service

router = APIRouter(
    prefix="/admin/accounts",
    tags=["admin-accounts"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.ADMIN))],
)


def _get_target(db: DbSession, user_id: uuid.UUID) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise NotFoundError("Account not found.")
    return target


@router.post("", response_model=UserPublic)
def create_account(
    payload: CreateAccountRequest, db: DbSession, current_user: CurrentUser
) -> UserPublic:
    user = auth_service.create_account(
        db,
        actor=current_user,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
    )
    return UserPublic.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=UserPublic)
def deactivate_account(
    user_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> UserPublic:
    target = _get_target(db, user_id)
    target = auth_service.deactivate_account(db, actor=current_user, target=target)
    return UserPublic.model_validate(target)


@router.post("/{user_id}/invitations", response_model=InvitationIssuedResponse)
def issue_invitation(
    user_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> InvitationIssuedResponse:
    target = _get_target(db, user_id)
    raw_token = auth_service.issue_invitation(db, actor=current_user, target=target)
    # Returned once to the Admin for out-of-band delivery (FR-AUTH-004); never logged.
    return InvitationIssuedResponse(activation_token=raw_token)


@router.post("/{user_id}/password-resets", response_model=PasswordResetIssuedResponse)
def issue_password_reset(
    user_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> PasswordResetIssuedResponse:
    target = _get_target(db, user_id)
    raw_token = auth_service.issue_password_reset(db, actor=current_user, target=target)
    return PasswordResetIssuedResponse(reset_token=raw_token)
