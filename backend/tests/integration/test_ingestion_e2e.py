"""AC-004 end to end on real PostgreSQL + pgvector + MinIO (fake OCR/embedder/tokenizer ports).

Markers: pg + minio.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.content import (
    ContentChunk,
    ContentType,
    ContentVersionStatus,
    IngestionStageRun,
    IngestionStatus,
)
from app.services import content_service
from app.services.ingestion.errors import EMPTY_EXTRACTION_MESSAGE
from app.services.ingestion.ports import OcrResult
from app.services.ingestion_runtime import ingest_version
from tests.support import docs
from tests.support.fakes import FakeEmbedder, FakeOcr, FakeTokenizer, RecordingQueue
from tests.support.world import build_world

pytestmark = [pytest.mark.pg, pytest.mark.minio]

SYLLABUS_OCR = (
    "Unit 1 Basics\n" + "arrays and linked lists " * 60 + "\nUnit 2 Trees\n" + "binary search trees " * 60
)


def _upload(db, world, store, cleanup, tmp_path, data, name, ctype=ContentType.SYLLABUS, unit_id=None):
    path = tmp_path / name
    path.write_bytes(data)
    version = content_service.upload_content(
        db,
        actor=world.co,
        subject_id=world.subject.id,
        content_type=ctype,
        title="Syllabus",
        unit_id=unit_id,
        all_units=unit_id is None and ctype != ContentType.SYLLABUS,
        content_asset_id=None,
        original_filename=name,
        declared_content_type=None,
        local_path=str(path),
        store=store,
        queue=RecordingQueue(),
    )
    cleanup.append(version.storage_key)
    return version


def test_ac004_scanned_syllabus_chunked_and_traceable(pg_session, minio_store, minio_cleanup, tmp_path):
    world = build_world(pg_session)
    version = _upload(
        pg_session, world, minio_store, minio_cleanup, tmp_path, docs.make_scanned_pdf(["x"]), "scan.pdf"
    )
    ocr = FakeOcr(lambda png: OcrResult(SYLLABUS_OCR, 92.0, "tesseract 5.3.0", "--oem 1 --psm 3"))
    result = ingest_version(
        pg_session, version.id, store=minio_store, ocr=ocr, tokenizer=FakeTokenizer(), embedder=FakeEmbedder()
    )
    assert result.status == "SUCCEEDED"
    pg_session.refresh(version)
    assert version.ingestion_status == IngestionStatus.SUCCEEDED and version.embedding_config_id is not None
    chunks = list(
        pg_session.scalars(
            select(ContentChunk)
            .where(ContentChunk.content_version_id == version.id)
            .order_by(ContentChunk.chunk_index)
        )
    )
    assert chunks and all(c.embedding is not None and len(c.embedding) == 1024 for c in chunks)
    assert {c.unit_no for c in chunks} == {1, 2}
    assert all(
        c.token_count <= 800 and c.locator.startswith("page:") and c.chunk_type == ContentType.SYLLABUS
        for c in chunks
    )
    assert all(c.subject_id == world.subject.id and c.source_file == "scan.pdf" for c in chunks)
    assert not any("binary" in c.text for c in chunks if c.unit_no == 1)  # never crosses the Unit boundary
    stages = {r.stage.value: r.status.value for r in pg_session.scalars(select(IngestionStageRun))}
    assert stages == {
        s: "SUCCEEDED" for s in ("VALIDATE", "EXTRACT", "OCR", "CLEAN", "CHUNK", "EMBED", "STORE")
    }


def test_ac004_negative_unreadable_scan_fails_no_empty_chunks(
    pg_session, minio_store, minio_cleanup, tmp_path
):
    world = build_world(pg_session)
    version = _upload(
        pg_session, world, minio_store, minio_cleanup, tmp_path, docs.make_scanned_pdf(["x", "y"]), "bad.pdf"
    )
    ocr = FakeOcr(lambda png: OcrResult("", 0.0, "tesseract 5.3.0", "cfg"))
    result = ingest_version(
        pg_session, version.id, store=minio_store, ocr=ocr, tokenizer=FakeTokenizer(), embedder=FakeEmbedder()
    )
    assert (result.status, result.failed_stage) == ("FAILED", "OCR")
    pg_session.refresh(version)
    assert version.ingestion_status == IngestionStatus.FAILED and version.failed_stage == "OCR"
    assert "bad.pdf" in version.failure_message and EMPTY_EXTRACTION_MESSAGE in version.failure_message
    assert pg_session.scalar(select(func.count()).select_from(ContentChunk)) == 0
    assert version.status == ContentVersionStatus.DRAFT


def test_failed_version_cannot_be_activated_and_retry_resumes(
    pg_session, minio_store, minio_cleanup, tmp_path
):
    world = build_world(pg_session)
    version = _upload(
        pg_session,
        world,
        minio_store,
        minio_cleanup,
        tmp_path,
        docs.make_txt("Arrays are contiguous. " * 40),
        "n.txt",
        ContentType.NOTES,
        world.units[0].id,
    )
    flaky = FakeEmbedder(fail_on_call=1)
    with pytest.raises(Exception, match="will retry"):
        ingest_version(
            pg_session,
            version.id,
            store=minio_store,
            ocr=FakeOcr(),
            tokenizer=FakeTokenizer(),
            embedder=flaky,
        )
    pg_session.refresh(version)
    assert version.ingestion_status == IngestionStatus.FAILED
    with pytest.raises(Exception, match="Ingestion must have succeeded"):
        content_service.activate_version(pg_session, actor=world.owner, version_id=version.id, reason=None)
    ingest_version(
        pg_session,
        version.id,
        store=minio_store,
        ocr=FakeOcr(),
        tokenizer=FakeTokenizer(),
        embedder=FakeEmbedder(),
    )
    pg_session.refresh(version)
    assert version.ingestion_status == IngestionStatus.SUCCEEDED
    content_service.activate_version(pg_session, actor=world.owner, version_id=version.id, reason="ok")
    assert version.status == ContentVersionStatus.ACTIVE


def test_ingest_is_idempotent_no_duplicate_chunks(pg_session, minio_store, minio_cleanup, tmp_path):
    world = build_world(pg_session)
    version = _upload(
        pg_session,
        world,
        minio_store,
        minio_cleanup,
        tmp_path,
        docs.make_txt("Trees. " * 50),
        "t.txt",
        ContentType.NOTES,
        world.units[1].id,
    )
    args = dict(store=minio_store, ocr=FakeOcr(), tokenizer=FakeTokenizer(), embedder=FakeEmbedder())
    ingest_version(pg_session, version.id, **args)
    n = pg_session.scalar(select(func.count()).select_from(ContentChunk))
    assert ingest_version(pg_session, version.id, **args).status == "SUCCEEDED"
    assert pg_session.scalar(select(func.count()).select_from(ContentChunk)) == n


def test_fixed_unit_upload_assigns_that_unit_to_all_chunks(pg_session, minio_store, minio_cleanup, tmp_path):
    world = build_world(pg_session)
    version = _upload(
        pg_session,
        world,
        minio_store,
        minio_cleanup,
        tmp_path,
        docs.make_docx([("Heading 1", "Intro"), ("Normal", "Graphs are nodes and edges. " * 30)]),
        "g.docx",
        ContentType.NOTES,
        world.units[2].id,
    )
    ingest_version(
        pg_session,
        version.id,
        store=minio_store,
        ocr=FakeOcr(),
        tokenizer=FakeTokenizer(),
        embedder=FakeEmbedder(),
    )
    units = set(
        pg_session.scalars(select(ContentChunk.unit_no).where(ContentChunk.content_version_id == version.id))
    )
    locs = set(
        pg_session.scalars(select(ContentChunk.locator).where(ContentChunk.content_version_id == version.id))
    )
    assert units == {3} and all(loc.startswith("section:") for loc in locs)


def test_tampered_object_fails_integrity_check(
    pg_session, minio_store, minio_cleanup, minio_root_client, tmp_path
):
    import io

    world = build_world(pg_session)
    version = _upload(
        pg_session,
        world,
        minio_store,
        minio_cleanup,
        tmp_path,
        docs.make_txt("original"),
        "o.txt",
        ContentType.NOTES,
        world.units[0].id,
    )
    minio_root_client.put_object(
        minio_store.bucket, version.storage_key, io.BytesIO(b"tampered!"), 9
    )  # root overwrite
    result = ingest_version(
        pg_session,
        version.id,
        store=minio_store,
        ocr=FakeOcr(),
        tokenizer=FakeTokenizer(),
        embedder=FakeEmbedder(),
    )
    assert (result.status, result.failed_stage) == ("FAILED", "VALIDATE")
