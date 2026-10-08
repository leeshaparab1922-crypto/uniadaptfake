from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.core.deps import CurrentUser, DbSession, RateLimiterDep, csrf_protect
from app.core.security import (
    clear_session_cookies,
    create_access_token,
    generate_csrf_token,
    set_session_cookies,
)
from app.schemas.auth import (
    GenericMessageResponse,
    InvitationConsumeRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetConsumeRequest,
    UserPublic,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: DbSession, rate_limiter: RateLimiterDep
) -> LoginResponse:
    user = auth_service.authenticate(
        db, email=payload.email, password=payload.password, ip=_client_ip(request), rate_limiter=rate_limiter
    )
    token, expires_at = create_access_token(
        user_id=str(user.id), role=user.role.value, token_version=user.token_version
    )
    csrf_token = generate_csrf_token()
    set_session_cookies(response, token=token, expires_at=expires_at, csrf_token=csrf_token)
    return LoginResponse(user=UserPublic.model_validate(user))


@router.post("/logout", response_model=GenericMessageResponse, dependencies=[Depends(csrf_protect)])
def logout(response: Response, db: DbSession, current_user: CurrentUser) -> GenericMessageResponse:
    auth_service.logout(db, current_user)
    clear_session_cookies(response)
    return GenericMessageResponse(message="Logged out.")


@router.get("/me", response_model=UserPublic)
def me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.post("/invitations/consume", response_model=GenericMessageResponse)
def consume_invitation(payload: InvitationConsumeRequest, db: DbSession) -> GenericMessageResponse:
    auth_service.consume_invitation(db, raw_token=payload.token, new_password=payload.new_password)
    return GenericMessageResponse(message="Account activated.")


@router.post("/password-reset/consume", response_model=GenericMessageResponse)
def consume_password_reset(
    payload: PasswordResetConsumeRequest, request: Request, db: DbSession, rate_limiter: RateLimiterDep
) -> GenericMessageResponse:
    auth_service.consume_password_reset(
        db,
        raw_token=payload.token,
        new_password=payload.new_password,
        ip=_client_ip(request),
        rate_limiter=rate_limiter,
    )
    return GenericMessageResponse(message="Password reset.")
