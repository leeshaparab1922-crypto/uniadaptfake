"""FR-AUTH-001/003/004. AC-029."""

from __future__ import annotations

import datetime as dt

import pytest

from app.core.errors import AuthenticationError, ForbiddenError, RateLimitedError
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services import auth_service


def _make_user(
    db_session, *, email="user@example.com", password="Secret123!", role=UserRole.STUDENT, active=True
) -> User:
    user = User(
        email=email,
        full_name="Test User",
        password_hash=hash_password(password),
        role=role,
        is_active=active,
        token_version=0,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _admin(db_session) -> User:
    return _make_user(db_session, email="admin@example.com", role=UserRole.ADMIN)


def test_authenticate_success(db_session, rate_limiter):
    user = _make_user(db_session)
    result = auth_service.authenticate(
        db_session, email=user.email, password="Secret123!", ip="1.2.3.4", rate_limiter=rate_limiter
    )
    assert result.id == user.id


def test_authenticate_wrong_password_generic_error(db_session, rate_limiter):
    _make_user(db_session)
    with pytest.raises(AuthenticationError) as exc:
        auth_service.authenticate(
            db_session, email="user@example.com", password="wrong", ip="1.2.3.4", rate_limiter=rate_limiter
        )
    assert exc.value.args[0] == auth_service.GENERIC_AUTH_FAILURE


def test_authenticate_unknown_account_same_generic_error(db_session, rate_limiter):
    with pytest.raises(AuthenticationError) as exc:
        auth_service.authenticate(
            db_session,
            email="nobody@example.com",
            password="whatever",
            ip="1.2.3.4",
            rate_limiter=rate_limiter,
        )
    assert exc.value.args[0] == auth_service.GENERIC_AUTH_FAILURE


def test_authenticate_inactive_account_rejected(db_session, rate_limiter):
    _make_user(db_session, active=False)
    with pytest.raises(AuthenticationError):
        auth_service.authenticate(
            db_session,
            email="user@example.com",
            password="Secret123!",
            ip="1.2.3.4",
            rate_limiter=rate_limiter,
        )


def test_login_throttle_after_repeated_failures(db_session, rate_limiter):
    _make_user(db_session)
    from app.core.config import settings

    limit = settings.rate_limit_login_per_account_per_window
    for _ in range(limit):
        with pytest.raises(AuthenticationError):
            auth_service.authenticate(
                db_session,
                email="user@example.com",
                password="wrong",
                ip="9.9.9.9",
                rate_limiter=rate_limiter,
            )
    with pytest.raises(RateLimitedError):
        auth_service.authenticate(
            db_session, email="user@example.com", password="wrong", ip="9.9.9.9", rate_limiter=rate_limiter
        )


def test_logout_revokes_token(db_session):
    user = _make_user(db_session)
    before = user.token_version
    auth_service.logout(db_session, user)
    assert user.token_version == before + 1


def test_deactivation_revokes_token(db_session):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    before = target.token_version
    auth_service.deactivate_account(db_session, actor=admin, target=target)
    assert target.token_version == before + 1
    assert target.is_active is False


def test_deactivation_by_non_admin_forbidden(db_session):
    non_admin = _make_user(db_session, email="teacher@example.com", role=UserRole.TEACHER)
    target = _make_user(db_session, email="target@example.com")
    with pytest.raises(ForbiddenError):
        auth_service.deactivate_account(db_session, actor=non_admin, target=target)


def test_invitation_single_use(db_session):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    raw_token = auth_service.issue_invitation(db_session, actor=admin, target=target)

    auth_service.consume_invitation(db_session, raw_token=raw_token, new_password="NewSecret123!")

    with pytest.raises(AuthenticationError):
        auth_service.consume_invitation(db_session, raw_token=raw_token, new_password="AnotherOne123!")


def test_invitation_expired_rejected(db_session):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    raw_token = auth_service.issue_invitation(db_session, actor=admin, target=target)

    from app.models.auth_tokens import InvitationToken

    token = db_session.query(InvitationToken).one()
    token.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(hours=1)
    db_session.commit()

    with pytest.raises(AuthenticationError):
        auth_service.consume_invitation(db_session, raw_token=raw_token, new_password="NewSecret123!")


def test_password_reset_revokes_token_and_invalidates_earlier_token(db_session, rate_limiter):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    before_version = target.token_version

    first_token = auth_service.issue_password_reset(db_session, actor=admin, target=target)
    second_token = auth_service.issue_password_reset(db_session, actor=admin, target=target)

    # The earlier reset token was invalidated by issuing a new one (NFR-SEC-015).
    with pytest.raises(AuthenticationError):
        auth_service.consume_password_reset(
            db_session,
            raw_token=first_token,
            new_password="NewSecret123!",
            ip="1.1.1.1",
            rate_limiter=rate_limiter,
        )

    auth_service.consume_password_reset(
        db_session,
        raw_token=second_token,
        new_password="NewSecret123!",
        ip="1.1.1.1",
        rate_limiter=rate_limiter,
    )
    assert target.token_version == before_version + 1


def test_password_reset_by_non_admin_forbidden(db_session):
    non_admin = _make_user(db_session, email="teacher@example.com", role=UserRole.TEACHER)
    target = _make_user(db_session, email="target@example.com")
    with pytest.raises(ForbiddenError):
        auth_service.issue_password_reset(db_session, actor=non_admin, target=target)


def test_consume_password_reset_replayed_token_rejected(db_session, rate_limiter):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    raw_token = auth_service.issue_password_reset(db_session, actor=admin, target=target)

    auth_service.consume_password_reset(
        db_session, raw_token=raw_token, new_password="NewSecret123!", ip="1.1.1.1", rate_limiter=rate_limiter
    )
    with pytest.raises(AuthenticationError):
        auth_service.consume_password_reset(
            db_session,
            raw_token=raw_token,
            new_password="Whatever123!",
            ip="1.1.1.1",
            rate_limiter=rate_limiter,
        )


def test_consume_password_reset_throttled_by_ip(db_session, rate_limiter):
    from app.core.config import settings

    limit = settings.rate_limit_token_consume_per_ip_per_window
    for _ in range(limit):
        with pytest.raises(AuthenticationError):
            auth_service.consume_password_reset(
                db_session,
                raw_token="bogus",
                new_password="Whatever123!",
                ip="5.5.5.5",
                rate_limiter=rate_limiter,
            )
    with pytest.raises(RateLimitedError):
        auth_service.consume_password_reset(
            db_session,
            raw_token="bogus",
            new_password="Whatever123!",
            ip="5.5.5.5",
            rate_limiter=rate_limiter,
        )


def test_create_account_duplicate_email_rejected(db_session):
    admin = _admin(db_session)
    _make_user(db_session, email="dup@example.com")
    from app.core.errors import ValidationError

    with pytest.raises(ValidationError):
        auth_service.create_account(
            db_session, actor=admin, email="dup@example.com", full_name="Someone", role=UserRole.STUDENT
        )


def test_create_account_by_non_admin_forbidden(db_session):
    non_admin = _make_user(db_session, email="teacher@example.com", role=UserRole.TEACHER)
    with pytest.raises(ForbiddenError):
        auth_service.create_account(
            db_session, actor=non_admin, email="new@example.com", full_name="Someone", role=UserRole.STUDENT
        )


def _audit_logs(db_session, action: str):
    from app.models.audit_log import AuditLog

    return db_session.query(AuditLog).filter(AuditLog.action == action).all()


def test_create_account_writes_audit_log(db_session):
    admin = _admin(db_session)
    account = auth_service.create_account(
        db_session, actor=admin, email="new@example.com", full_name="Someone", role=UserRole.STUDENT
    )
    logs = _audit_logs(db_session, "CREATE_ACCOUNT")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(account.id)


def test_deactivate_account_writes_audit_log(db_session):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    auth_service.deactivate_account(db_session, actor=admin, target=target)
    logs = _audit_logs(db_session, "DEACTIVATE_ACCOUNT")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(target.id)


def test_issue_invitation_writes_audit_log(db_session):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    auth_service.issue_invitation(db_session, actor=admin, target=target)
    logs = _audit_logs(db_session, "ISSUE_INVITATION")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(target.id)


def test_issue_password_reset_writes_audit_log(db_session):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    auth_service.issue_password_reset(db_session, actor=admin, target=target)
    logs = _audit_logs(db_session, "ISSUE_PASSWORD_RESET")
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].entity_id == str(target.id)


def test_consume_invitation_writes_audit_log(db_session):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    raw_token = auth_service.issue_invitation(db_session, actor=admin, target=target)
    user = auth_service.consume_invitation(db_session, raw_token=raw_token, new_password="NewSecret123!")
    logs = _audit_logs(db_session, "CONSUME_INVITATION")
    assert len(logs) == 1
    assert logs[0].actor_id == user.id
    assert logs[0].entity_id == str(user.id)


def test_consume_password_reset_writes_audit_log(db_session, rate_limiter):
    admin = _admin(db_session)
    target = _make_user(db_session, email="target@example.com")
    raw_token = auth_service.issue_password_reset(db_session, actor=admin, target=target)
    user = auth_service.consume_password_reset(
        db_session, raw_token=raw_token, new_password="NewSecret123!", ip="1.1.1.1", rate_limiter=rate_limiter
    )
    logs = _audit_logs(db_session, "CONSUME_PASSWORD_RESET")
    assert len(logs) == 1
    assert logs[0].actor_id == user.id
    assert logs[0].entity_id == str(user.id)


def test_logout_writes_audit_log(db_session):
    user = _make_user(db_session)
    auth_service.logout(db_session, user)
    logs = _audit_logs(db_session, "LOGOUT")
    assert len(logs) == 1
    assert logs[0].actor_id == user.id
    assert logs[0].entity_id == str(user.id)
