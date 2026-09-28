"""Shared pytest fixtures.

Uses an in-memory SQLite engine instead of PostgreSQL for the test suite,
because Docker/Postgres/Redis are unavailable in this execution
environment (see the "Test environment" deviation note in
`docs/phases/phase-1-foundation/plan.md`). Production always runs on
PostgreSQL 15 per Section 5's fixed stack - Alembic migration `0001` and
`docker-compose.yml` target Postgres exclusively; SQLite here is a
test-only substitute for the ORM-level service/API suite.

Similarly, `FakeRedis` is a small in-memory stand-in for the two Redis
calls `RateLimiter` makes (`incr`/`expire`), used because no Redis server
is reachable here - it avoids adding a `fakeredis` dependency purely for
tests. Production `RateLimiter` always talks to a real Redis instance via
`app.core.rate_limit.get_redis_client`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register every model on Base.metadata
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.db.base import Base
from app.db.session import get_db


class FakeRedis:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def incr(self, name: str) -> int:
        self._counters[name] = self._counters.get(name, 0) + 1
        return self._counters[name]

    def expire(self, name: str, seconds: int) -> bool:
        return True


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine) -> Session:
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture()
def rate_limiter(fake_redis: FakeRedis) -> RateLimiter:
    return RateLimiter(fake_redis)


@pytest.fixture()
def client(engine):
    from app.core.config import settings
    from app.main import create_app

    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def _get_db_override():
        session = testing_session_local()
        try:
            yield session
        finally:
            session.close()

    fake = FakeRedis()

    def _get_rate_limiter_override() -> RateLimiter:
        return RateLimiter(fake)

    # TestClient talks to the app over plain HTTP ("http://testserver"), and
    # a `Secure`-flagged cookie is never sent back by the client's cookie
    # jar over plain HTTP (ADR-0001 requires `Secure` in real deployments,
    # where TLS terminates in front of the app). Disable it only for this
    # fixture's app instance, exactly like local HTTP development already
    # does via `COOKIE_SECURE=false` in `.env`.
    previous_cookie_secure = settings.cookie_secure
    settings.cookie_secure = False

    fastapi_app = create_app()
    fastapi_app.dependency_overrides[get_db] = _get_db_override
    fastapi_app.dependency_overrides[get_rate_limiter] = _get_rate_limiter_override

    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        settings.cookie_secure = previous_cookie_secure
