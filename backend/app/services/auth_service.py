"""Login, token issuance/validation, account administration, and
invitation/password-reset issuance+consumption. FR-AUTH-001..004.

Not one of the SRS's five named deterministic services, but kept as pure,
DB-session-scoped business logic separated from the route layer per
`.claude/rules/backend.md`.

Public-facing failures (`AuthenticationError`) always use a generic message
- callers must never be able to distinguish "wrong password" from "unknown
account" from "expired token" (NFR-SEC-016).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    AuthenticationError,
    ForbiddenError,
    RateLimitedError,
    ValidationError,
)
from app.core.rate_limit import RateLimiter
from app.core.security import (
    generate_raw_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth_tokens import InvitationToken, PasswordResetToken
from app.models.user import User, UserRole
from app.services import audit

GENERIC_AUTH_FAILURE = "Invalid credentials or account unavailable."
GENERIC_TOKEN_FAILURE = "This link is invalid or has expired."


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite (used only by this phase's test suite - see plan.md's "Test
    environment" note) round-trips `DateTime(timezone=True)` values as
    naive datetimes, unlike PostgreSQL. Normalize before comparing against
    an aware `datetime.now(timezone.utc)` so expiry checks work on both."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _record_audit(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None,
) -> None:
    """Thin wrapper over the shared `app.services.audit.record` helper
    (ADR-0011) - kept so every call site below stays unchanged in shape."""
    audit.record(
        db,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        reason=reason,
    )


def authenticate(db: Session, *, email: str, password: str, ip: str, rate_limiter: RateLimiter) -> User:
    """FR-AUTH-001: verify bcrypt hash, enforce account+IP throttling
    (NFR-SEC-016), never disclose which check failed."""
    account_ok = rate_limiter.hit(
        f"rl:login:acct:{email.lower()}",
        limit=settings.rate_limit_login_per_account_per_window,
        window_seconds=settings.rate_limit_window_seconds,
    )
    ip_ok = rate_limiter.hit(
        f"rl:login:ip:{ip}",
        limit=settings.rate_limit_login_per_ip_per_window,
        window_seconds=settings.rate_limit_window_seconds,
    )
    if not account_ok or not ip_ok:
        raise RateLimitedError(GENERIC_AUTH_FAILURE)

    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthenticationError(GENERIC_AUTH_FAILURE)
    return user


def logout(db: Session, user: User) -> None:
    """Increments token_version so the just-cleared cookie's JWT is rejected
    immediately even if replayed (NFR-SEC-004)."""
    user.token_version += 1
    _record_audit(db, actor=user, action="LOGOUT", entity_type="User", entity_id=user.id)
    db.commit()


def create_account(db: Session, *, actor: User, email: str, full_name: str, role: UserRole) -> User:
    """FR-AUTH-003: Admin-only. Exactly one role per account. The password
    hash is an unusable placeholder until the invited user consumes their
    invitation token and sets their own password."""
    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only Admin may create accounts.")
    email_norm = email.lower()
    if db.scalar(select(User).where(User.email == email_norm)) is not None:
        raise ValidationError("An account with this email already exists.")
    user = User(
        email=email_norm,
        full_name=full_name,
        role=role,
        password_hash=hash_password(uuid.uuid4().hex),
        is_active=True,
        token_version=0,
    )
    db.add(user)
    db.flush()
    _record_audit(
        db,
        actor=actor,
        action="CREATE_ACCOUNT",
        entity_type="User",
        entity_id=user.id,
        after={"email": user.email, "role": role.value},
    )
    db.commit()
    return user


def deactivate_account(db: Session, *, actor: User, target: User) -> User:
    """AC: a deactivated account cannot log in - revokes any outstanding JWT
    immediately via token_version (NFR-SEC-004)."""
    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only Admin may deactivate accounts.")
    target.is_active = False
    target.token_version += 1
    _record_audit(
        db,
        actor=actor,
        action="DEACTIVATE_ACCOUNT",
        entity_type="User",
        entity_id=target.id,
    )
    db.commit()
    return target


def issue_invitation(db: Session, *, actor: User, target: User) -> str:
    """FR-AUTH-004: single-use, expiring; only the hash is stored
    (NFR-SEC-015). Returns the raw token once, for the Admin to deliver
    out-of-band - callers must never log it."""
    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only Admin may issue invitations.")
    raw_token = generate_raw_token()
    now = datetime.now(UTC)
    db.add(
        InvitationToken(
            user_id=target.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(hours=settings.invitation_token_ttl_hours),
        )
    )
    target.invited_at = now
    _record_audit(
        db,
        actor=actor,
        action="ISSUE_INVITATION",
        entity_type="User",
        entity_id=target.id,
    )
    db.commit()
    return raw_token


def consume_invitation(db: Session, *, raw_token: str, new_password: str) -> User:
    token_hash = hash_token(raw_token)
    token = db.scalar(select(InvitationToken).where(InvitationToken.token_hash == token_hash))
    now = datetime.now(UTC)
    if token is None or token.used_at is not None or _as_aware_utc(token.expires_at) < now:
        raise AuthenticationError(GENERIC_TOKEN_FAILURE)
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(GENERIC_TOKEN_FAILURE)
    user.password_hash = hash_password(new_password)
    user.activated_at = now
    user.token_version += 1
    token.used_at = now
    _record_audit(
        db,
        actor=user,
        action="CONSUME_INVITATION",
        entity_type="User",
        entity_id=user.id,
    )
    db.commit()
    return user


def issue_password_reset(db: Session, *, actor: User, target: User) -> str:
    """FR-AUTH-004: Admin-triggered (the SRS's reset flow has the Admin
    generate/select the token; there is no public self-service "forgot
    password by email" endpoint since email/SMS delivery is explicitly not
    required). Invalidates any earlier unused reset token for this user."""
    if actor.role != UserRole.ADMIN:
        raise ForbiddenError("Only Admin may issue password resets.")
    now = datetime.now(UTC)
    earlier = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == target.id,
            PasswordResetToken.used_at.is_(None),
        )
    ).all()
    for t in earlier:
        t.used_at = now
    raw_token = generate_raw_token()
    db.add(
        PasswordResetToken(
            user_id=target.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(hours=settings.password_reset_token_ttl_hours),
        )
    )
    _record_audit(
        db,
        actor=actor,
        action="ISSUE_PASSWORD_RESET",
        entity_type="User",
        entity_id=target.id,
    )
    db.commit()
    return raw_token


def consume_password_reset(
    db: Session,
    *,
    raw_token: str,
    new_password: str,
    ip: str,
    rate_limiter: RateLimiter,
) -> User:
    ip_ok = rate_limiter.hit(
        f"rl:reset-consume:ip:{ip}",
        limit=settings.rate_limit_token_consume_per_ip_per_window,
        window_seconds=settings.rate_limit_window_seconds,
    )
    if not ip_ok:
        raise RateLimitedError(GENERIC_TOKEN_FAILURE)

    token_hash = hash_token(raw_token)
    token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    now = datetime.now(UTC)
    if token is None or token.used_at is not None or _as_aware_utc(token.expires_at) < now:
        raise AuthenticationError(GENERIC_TOKEN_FAILURE)
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(GENERIC_TOKEN_FAILURE)
    user.password_hash = hash_password(new_password)
    user.token_version += 1  # NFR-SEC-004/015: reset revokes any prior session immediately.
    user.last_reset_at = now
    token.used_at = now
    _record_audit(
        db,
        actor=user,
        action="CONSUME_PASSWORD_RESET",
        entity_type="User",
        entity_id=user.id,
    )
    db.commit()
    return user
