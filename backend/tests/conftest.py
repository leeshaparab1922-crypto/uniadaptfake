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

import os

# The prompt-registry sync (ADR-0017) needs the Phase 2 tables, which only exist on PostgreSQL.
# SQLite-backed apps skip it; the PG tests that cover it call `sync_prompts` directly.
os.environ.setdefault("PROMPT_SYNC_ON_STARTUP", "false")

import pytest  # noqa: E402
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
    # Phase 2 tables (pgvector/partial indexes) are PostgreSQL-only: skipped here, and every
    # Phase 2 DB test uses the `pg_*` fixtures below against the compose Postgres service.
    sqlite_tables = [t for t in Base.metadata.sorted_tables if not t.info.get("pg_only")]
    Base.metadata.create_all(eng, tables=sqlite_tables)
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


# ---------------------------------------------------------------------------
# Phase 2: real PostgreSQL (pgvector) and MinIO fixtures (docker-compose services).
#
#   docker compose up -d --wait postgres minio && docker compose run --rm minio-init
#
# An unreachable service FAILS the test (never silently skips) unless
# UNIADAPT_TEST_ALLOW_SKIP=1 is set explicitly (developer machines without Docker).
# ---------------------------------------------------------------------------
import os  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402

from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app.core.deps import (  # noqa: E402
    get_curriculum_queue,
    get_embedder,
    get_ingestion_queue,
    get_object_store,
)

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_SETUP_HINT = "Run: docker compose up -d --wait postgres minio && docker compose run --rm minio-init"


def _service_unavailable(message: str):
    if os.getenv("UNIADAPT_TEST_ALLOW_SKIP") == "1":
        pytest.skip(message)
    pytest.fail(f"{message}. {_SETUP_HINT}", pytrace=False)


def _test_database_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL", "postgresql+psycopg://uniadapt:uniadapt@localhost:5432/uniadapt_test"
    )


@pytest.fixture(scope="session")
def pg_engine():
    """Fresh `uniadapt_test` database built by `alembic upgrade head` (never `create_all`)."""
    from alembic.config import Config

    from alembic import command

    url = make_url(_test_database_url())
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    except OperationalError as exc:
        admin.dispose()
        _service_unavailable(f"PostgreSQL is not reachable at {url.host}:{url.port} ({type(exc).__name__})")
    admin.dispose()

    from app.core.config import settings

    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    previous = settings.database_url
    settings.database_url = url.render_as_string(hide_password=False)
    try:
        command.upgrade(cfg, "head")
    finally:
        settings.database_url = previous

    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_session(pg_engine) -> Session:
    """Per-test session inside an outer transaction that is rolled back; service-layer
    `commit()` calls only release a SAVEPOINT."""
    connection = pg_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def pg_committed(pg_engine):
    """Sessionmaker whose commits are real (for concurrency / Celery-style tests); all data is
    truncated afterwards."""
    factory = sessionmaker(bind=pg_engine, autoflush=False, future=True)
    yield factory
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with pg_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def minio_store():
    """Real MinIO via the scoped *test* credential, whose policy covers only the test bucket
    (finding N6). It has the same rights there as the app credential has on the content bucket."""
    from minio import Minio

    from app.integrations.object_store import MinioObjectStore

    endpoint = os.getenv("TEST_MINIO_ENDPOINT", "localhost:9000")
    access = os.getenv("TEST_MINIO_ACCESS_KEY") or "uniadapt-test"
    secret = os.getenv("TEST_MINIO_SECRET_KEY") or ""
    bucket = os.getenv("TEST_MINIO_BUCKET") or "uniadapt-content-test"
    if not secret:
        _service_unavailable(
            "TEST_MINIO_SECRET_KEY is not set; set it in the repo-root .env before running "
            "minio-init, which creates the test user from it"
        )
    client = Minio(endpoint, access_key=access, secret_key=secret, secure=False)
    try:
        if not client.bucket_exists(bucket):
            raise RuntimeError(f"bucket {bucket!r} missing (minio-init not run)")
    except Exception as exc:  # noqa: BLE001 - any connectivity/permission problem
        _service_unavailable(f"MinIO is not usable at {endpoint} ({type(exc).__name__}: {exc})")
    return MinioObjectStore(client, bucket)


@pytest.fixture(scope="session")
def minio_root_client():
    """Root MinIO client for test cleanup/assertions only (the app credential cannot delete)."""
    from minio import Minio

    return Minio(
        os.getenv("TEST_MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("TEST_MINIO_ROOT_USER") or "minioadmin",
        secret_key=os.getenv("TEST_MINIO_ROOT_PASSWORD") or "minioadmin",
        secure=False,
    )


@pytest.fixture()
def minio_cleanup(minio_store, minio_root_client):
    """Collects keys written by a test and deletes them afterwards."""
    keys: list[str] = []
    yield keys
    for key in keys:
        minio_root_client.remove_object(minio_store.bucket, key)


class _ForbiddenStore:
    def __getattr__(self, name):
        raise AssertionError("This test must not touch object storage")


def _make_pg_client(pg_session, store, queue, curriculum_queue=None, embedder=None):
    from app.core.config import settings
    from app.main import create_app

    fake = FakeRedis()
    previous = settings.cookie_secure
    settings.cookie_secure = False
    fastapi_app = create_app()

    def _db():
        yield pg_session

    fastapi_app.dependency_overrides[get_db] = _db
    fastapi_app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(fake)
    fastapi_app.dependency_overrides[get_object_store] = lambda: store
    fastapi_app.dependency_overrides[get_ingestion_queue] = lambda: queue
    # Slice 2B: curriculum generation is queued to a recorder and Topics are embedded by a fake.
    if curriculum_queue is not None:
        fastapi_app.dependency_overrides[get_curriculum_queue] = lambda: curriculum_queue
    if embedder is not None:
        fastapi_app.dependency_overrides[get_embedder] = lambda: embedder
    return fastapi_app, previous


@pytest.fixture()
def queue_recorder():
    from tests.support.fakes import RecordingQueue

    return RecordingQueue()


@pytest.fixture()
def curriculum_queue_recorder():
    from tests.support.fakes import RecordingQueue

    return RecordingQueue()


@pytest.fixture()
def pg_client(pg_session, queue_recorder, curriculum_queue_recorder):
    """API client on real Postgres; object storage is forbidden (use `pg_minio_client` for uploads)."""
    from app.core.config import settings
    from tests.support.fakes import FakeEmbedder

    app_, previous = _make_pg_client(
        pg_session, _ForbiddenStore(), queue_recorder, curriculum_queue_recorder, FakeEmbedder()
    )
    try:
        with TestClient(app_) as c:
            yield c
    finally:
        settings.cookie_secure = previous


@pytest.fixture()
def pg_minio_client(pg_session, minio_store, queue_recorder, curriculum_queue_recorder):
    """API client on real Postgres + real MinIO."""
    from app.core.config import settings
    from tests.support.fakes import FakeEmbedder

    app_, previous = _make_pg_client(
        pg_session, minio_store, queue_recorder, curriculum_queue_recorder, FakeEmbedder()
    )
    try:
        with TestClient(app_) as c:
            yield c
    finally:
        settings.cookie_secure = previous


def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]
