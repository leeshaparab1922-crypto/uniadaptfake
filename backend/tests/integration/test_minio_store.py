"""ADR-0018 against the real compose MinIO service. Marker: minio.

The app credential is the scoped one created by `minio-init`; the root client is used only to
verify state and clean up (the scoped policy deliberately cannot delete or overwrite).
"""

from __future__ import annotations

import hashlib
import io
import uuid

import pytest
from minio.error import S3Error

from app.integrations.object_store import MinioObjectStore, build_storage_key
from app.services.ingestion.ports import ObjectAlreadyExistsError

pytestmark = pytest.mark.minio


def _key(ext="txt"):
    return build_storage_key(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), ext)


def _put(store, key, data: bytes, content_type="text/plain"):
    store.put_if_absent(key, io.BytesIO(data), len(data), content_type)


def test_put_get_roundtrip_with_sha256_integrity(minio_store, minio_cleanup, tmp_path):
    key, data = _key(), b"hello syllabus " * 100
    minio_cleanup.append(key)
    _put(minio_store, key, data)
    dest = tmp_path / "out.txt"
    minio_store.download_to(key, str(dest))
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == hashlib.sha256(data).hexdigest()
    assert minio_store.stat_size(key) == len(data)


def test_write_once_key_second_put_rejected(minio_store, minio_cleanup, tmp_path):
    key = _key()
    minio_cleanup.append(key)
    _put(minio_store, key, b"original")
    with pytest.raises(ObjectAlreadyExistsError):
        _put(minio_store, key, b"overwrite attempt")
    dest = tmp_path / "o.txt"
    minio_store.download_to(key, str(dest))
    assert dest.read_bytes() == b"original"


def test_exists_distinguishes_present_and_absent_keys(minio_store, minio_cleanup):
    key = _key()
    assert minio_store.exists(key) is False
    minio_cleanup.append(key)
    _put(minio_store, key, b"x")
    assert minio_store.exists(key) is True


def test_key_layout_follows_adr_0018_in_the_bucket(minio_store, minio_cleanup, minio_root_client):
    sid, aid, vid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    key = build_storage_key(sid, aid, vid, "pdf")
    minio_cleanup.append(key)
    _put(minio_store, key, b"%PDF-1.4", "application/pdf")
    names = [
        o.object_name
        for o in minio_root_client.list_objects(minio_store.bucket, prefix=f"subjects/{sid}/", recursive=True)
    ]
    assert names == [f"subjects/{sid}/assets/{aid}/versions/{vid}/original.pdf"]


def test_bucket_is_private_anonymous_access_denied(minio_store, minio_cleanup):
    import urllib.error
    import urllib.request

    key = _key()
    minio_cleanup.append(key)
    _put(minio_store, key, b"secret")
    scheme = "https" if minio_store._client._base_url.is_https else "http"  # noqa: SLF001
    url = f"{scheme}://{minio_store._client._base_url.host}/{minio_store.bucket}/{key}"  # noqa: SLF001
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(url)  # noqa: S310 - local test service
    assert exc.value.code in (401, 403)


def test_scoped_credential_cannot_touch_other_buckets(minio_store, minio_root_client):
    other = f"uniadapt-other-{uuid.uuid4().hex[:8]}"
    minio_root_client.make_bucket(other)
    try:
        minio_root_client.put_object(other, "x.txt", io.BytesIO(b"x"), 1)
        foreign = MinioObjectStore(minio_store._client, other)  # noqa: SLF001
        with pytest.raises(S3Error):
            foreign.exists("x.txt")
        with pytest.raises(S3Error):
            _put(foreign, "y.txt", b"y")
    finally:
        minio_root_client.remove_object(other, "x.txt")
        minio_root_client.remove_bucket(other)


def test_scoped_credential_cannot_delete_objects(minio_store, minio_cleanup):
    key = _key()
    minio_cleanup.append(key)
    _put(minio_store, key, b"keep me")
    with pytest.raises(S3Error):
        minio_store._client.remove_object(minio_store.bucket, key)  # noqa: SLF001
    assert minio_store.exists(key)


def test_scoped_credential_is_not_the_root_credential(minio_store):
    import os

    assert (os.getenv("TEST_MINIO_ACCESS_KEY") or "uniadapt-test") != (
        os.getenv("TEST_MINIO_ROOT_USER") or "minioadmin"
    )
    with pytest.raises(S3Error):  # root-only admin operation must fail for the app key
        minio_store._client.make_bucket(f"uniadapt-forbidden-{uuid.uuid4().hex[:6]}")  # noqa: SLF001


@pytest.mark.pg
def test_only_original_objects_exist_under_a_version_prefix_no_derived_artifacts(
    minio_store, minio_cleanup, minio_root_client, pg_session, tmp_path
):
    """Derived artifacts (OCR images, extracted text) are never written to MinIO (ADR-0018)."""
    from app.services import content_service
    from app.services.ingestion_runtime import ingest_version
    from tests.support import docs
    from tests.support.fakes import FakeEmbedder, FakeOcr, FakeTokenizer, RecordingQueue
    from tests.support.world import build_world

    world = build_world(pg_session)
    path = tmp_path / "scan.pdf"
    path.write_bytes(docs.make_scanned_pdf(["Unit 1 text"]))
    from app.models.content import ContentType
    from app.services.ingestion.ports import OcrResult

    version = content_service.upload_content(
        pg_session,
        actor=world.co,
        subject_id=world.subject.id,
        content_type=ContentType.NOTES,
        title="Scan",
        unit_id=world.units[0].id,
        content_asset_id=None,
        original_filename="scan.pdf",
        declared_content_type=None,
        local_path=str(path),
        store=minio_store,
        queue=RecordingQueue(),
    )
    minio_cleanup.append(version.storage_key)
    ocr = FakeOcr(lambda png: OcrResult("Unit 1 " + "words " * 20, 90.0, "fake", "cfg"))
    ingest_version(
        pg_session, version.id, store=minio_store, ocr=ocr, tokenizer=FakeTokenizer(), embedder=FakeEmbedder()
    )
    prefix = f"subjects/{world.subject.id}/"
    names = [
        o.object_name
        for o in minio_root_client.list_objects(minio_store.bucket, prefix=prefix, recursive=True)
    ]
    assert names == [version.storage_key] and names[0].endswith("/original.pdf")


def test_test_credential_cannot_reach_the_content_bucket(minio_store):
    """Finding N6: each scoped policy covers exactly one bucket (ADR-0018 rule 4)."""
    import os

    content_bucket = os.getenv("MINIO_BUCKET") or "uniadapt-content"
    with pytest.raises(S3Error):
        list(minio_store._client.list_objects(content_bucket))  # noqa: SLF001
