"""ADR-0018 key layout (pure builder; MinIO behaviour is tested in tests/integration/test_minio_store.py)."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import Settings
from app.integrations.object_store import build_storage_key


def test_key_layout_matches_adr_0018():
    s, a, v = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    assert build_storage_key(s, a, v, "pdf") == f"subjects/{s}/assets/{a}/versions/{v}/original.pdf"


def test_extension_comes_from_validated_type_only():
    ids = [uuid.uuid4()] * 3
    for bad in ("exe", "PDF", "../x", "pdf/../../etc", ""):
        with pytest.raises(ValueError):
            build_storage_key(*ids, bad)


def test_ids_must_be_uuids_so_user_text_cannot_reach_a_key():
    ok = uuid.uuid4()
    with pytest.raises(ValueError):
        build_storage_key("../../etc", ok, ok, "pdf")


def test_each_version_gets_a_distinct_key():
    s, a = uuid.uuid4(), uuid.uuid4()
    assert build_storage_key(s, a, uuid.uuid4(), "txt") != build_storage_key(s, a, uuid.uuid4(), "txt")


@pytest.mark.parametrize("environment", ["development", "test"])
def test_dev_and_test_never_fall_back_to_the_root_credential(environment):
    s = Settings(
        environment=environment,
        minio_app_access_key="",
        minio_app_secret_key="",
    )
    with pytest.raises(ValueError, match="MINIO_APP_ACCESS_KEY"):
        _ = s.effective_minio_access_key
    with pytest.raises(ValueError, match="MINIO_APP_SECRET_KEY"):
        _ = s.effective_minio_secret_key


def test_scoped_credential_required_in_production():
    prod = Settings(
        environment="production",
        jwt_secret_key="x" * 40,
        minio_app_access_key="",
        minio_app_secret_key="",
    )
    with pytest.raises(ValueError, match="MINIO_APP_ACCESS_KEY"):
        _ = prod.effective_minio_access_key
    scoped = Settings(
        environment="production",
        jwt_secret_key="x" * 40,
        minio_app_access_key="app",
        minio_app_secret_key="s",
    )
    assert scoped.effective_minio_access_key == "app"


def test_default_embedding_revision_is_a_pinned_commit_hash():
    s = Settings()
    assert s.embedding_model_id == "BAAI/bge-m3"
    assert len(s.embedding_model_revision) == 40 and set(s.embedding_model_revision) <= set(
        "0123456789abcdef"
    )
    assert (s.chunk_max_tokens, s.chunk_overlap_tokens) == (800, 120)


def test_missing_storage_credential_is_a_generic_503_not_a_settings_leak(monkeypatch):
    """Finding N6: the Teacher never sees setting names; the details go to the server log."""
    from app.core import deps
    from app.core.config import settings
    from app.core.errors import ServiceUnavailableError

    monkeypatch.setattr(settings, "minio_app_access_key", "")
    with pytest.raises(ServiceUnavailableError) as info:
        deps.get_object_store()
    assert "MINIO" not in str(info.value)
    assert str(info.value) == deps.STORAGE_UNAVAILABLE_MESSAGE


def test_service_unavailable_maps_to_503():
    from app.core.errors import ServiceUnavailableError
    from app.main import _ERROR_STATUS_MAP

    assert _ERROR_STATUS_MAP[ServiceUnavailableError] == 503
