"""Password hashing, JWT issuance/validation, and cookie/CSRF helpers.

- bcrypt only for password hashing (Section 5 fixed stack; NFR-SEC-005).
  Uses the `bcrypt` package directly rather than a `passlib` wrapper: this
  is a deliberate deviation from plan.md's file-list wording
  ("passlib[bcrypt]") - see the "Implementation deviations" note added to
  `docs/phases/phase-1-foundation/plan.md` for the reasoning (a documented
  passlib/bcrypt>=4.1 compatibility issue, and bcrypt is the literally
  SRS-named technology).
- PyJWT for JWT (ADR-0010): 4-hour expiry, no refresh token, `token_version`
  claim for revocation (NFR-SEC-004).
- JWT travels in an httpOnly/Secure/SameSite=Strict cookie with a
  double-submit CSRF cookie/header pair (ADR-0001).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE_NAME = "uniadapt_session"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    *, user_id: str, role: str, token_version: int
) -> tuple[str, datetime]:
    """Issues a 4-hour JWT with identity, exactly one role, and a
    token-version claim (FR-AUTH-001). No refresh token is ever issued."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "token_version": token_version,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises `jwt.PyJWTError` (or a subclass) on any invalid/expired token."""
    return jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def generate_raw_token() -> str:
    """Single-use invitation/reset token. Only the hash is ever persisted
    (NFR-SEC-015) - the raw value is returned once to the caller (Admin) for
    out-of-band delivery and is never logged."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def set_session_cookies(
    response: Response, *, token: str, expires_at: datetime, csrf_token: str
) -> None:
    max_age = int(settings.jwt_expires_minutes * 60)
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
        domain=settings.cookie_domain,
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", domain=settings.cookie_domain)
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", domain=settings.cookie_domain)
