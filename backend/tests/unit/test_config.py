"""NFR-SEC-004/013: JWT secret hardening outside development/test."""

from __future__ import annotations

import pytest

from app.core.config import Settings


def test_placeholder_secret_rejected_outside_dev_test():
    with pytest.raises(ValueError):
        Settings(environment="production", jwt_secret_key="change-me-in-env")


def test_short_secret_rejected_outside_dev_test():
    with pytest.raises(ValueError):
        Settings(environment="production", jwt_secret_key="short-secret")


def test_strong_secret_accepted_in_production():
    settings = Settings(environment="production", jwt_secret_key="x" * 32)
    assert settings.environment == "production"


def test_placeholder_secret_allowed_in_development():
    settings = Settings(environment="development", jwt_secret_key="change-me-in-env")
    assert settings.jwt_secret_key == "change-me-in-env"
