"""Environment-driven settings (Pydantic v2 Settings).

python-dotenv loads `.env` in local development only (ADR-0010); in Docker
and production, real environment variables are used instead.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_JWT_SECRET = "change-me-in-env"
MIN_JWT_SECRET_BYTES = 32
_NON_PRODUCTION_ENVIRONMENTS = {"development", "test"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+psycopg://uniadapt:uniadapt@localhost:5432/uniadapt"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 240  # NFR-SEC-004: 4-hour access token, no refresh token.

    bcrypt_rounds: int = 12

    cookie_secure: bool = True  # Disable only for local HTTP development.
    cookie_domain: str | None = None
    cors_allowed_origin: str = "http://localhost:5173"

    # ADR-0006: fixed-window rate limiting, limits/window configurable via env, not hard-coded.
    rate_limit_window_seconds: int = 900
    rate_limit_login_per_account_per_window: int = 5
    rate_limit_login_per_ip_per_window: int = 20
    rate_limit_token_consume_per_ip_per_window: int = 20

    invitation_token_ttl_hours: int = 72
    password_reset_token_ttl_hours: int = 2

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    @model_validator(mode="after")
    def _reject_weak_jwt_secret_outside_dev_test(self) -> Settings:
        """NFR-SEC-004/013: a 4-hour JWT signed with a short or placeholder
        secret is trivially forgeable. Refuse to start with one outside
        development/test - `.env.example` documents the required override."""
        if self.environment.lower() not in _NON_PRODUCTION_ENVIRONMENTS:
            if self.jwt_secret_key == PLACEHOLDER_JWT_SECRET:
                raise ValueError(
                    "JWT_SECRET_KEY is still the placeholder value; set a real "
                    "secret before starting outside development/test."
                )
            if len(self.jwt_secret_key.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_BYTES} bytes "
                    "outside development/test."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
