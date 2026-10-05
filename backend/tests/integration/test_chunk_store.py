"""FR-CON-002/003: chunk storage in pgvector with mandatory metadata. Marker: pg."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DataError, IntegrityError, StatementError

from app.models.content import ContentChunk, ContentType, ContentVersionStatus, IngestionStatus, LocatorType
from tests.support.content_helpers import make_asset, make_chunk, make_embedding_config, make_version
from tests.support.fakes import FakeEmbedder
from tests.support.world import build_world

pytestmark = pytest.mark.pg


def _insert_raw(db, *, version, subject_id, config, **overrides):
    """INSERT a chunk row with raw SQL, bypassing ORM validation, so the NOT NULL / CHECK under
    test is the only thing that can reject it. UPDATE-based checks would now hit the chunk
    immutability trigger first (finding N7)."""
    import hashlib
    import uuid

    from sqlalchemy import text

    row = {
        "id": uuid.uuid4(),
        "subject_id": subject_id,
        "content_version_id": version.id,
        "unit_no": 1,
        "source_file": version.original_filename,
        "locator_type": "PAGE",
        "locator": "page:1",
        "page_no": 1,
        "chunk_type": "NOTES",
        "chunk_index": 0,
        "text": "x",
        "token_count": 1,
        "text_sha256": hashlib.sha256(b"x").hexdigest(),
        "embedding_config_id": config.id,
        **overrides,
    }
    columns = ", ".join(row)
    values = ", ".join(f":{k}" for k in row)
    with db.begin_nested():
        db.execute(text(f"INSERT INTO content_chunks ({columns}) VALUES ({values})"), row)


def _setup(db):
    world = build_world(db)
    asset = make_asset(db, subject_id=world.subject.id, actor=world.co)
    version = make_version(db, asset=asset, actor=world.co, version_no=1)
    return world, asset, version, make_embedding_config(db)


def test_every_chunk_has_all_metadata_fields(pg_session):
    world, _, version, cfg = _setup(pg_session)
    chunk = make_chunk(
        pg_session,
        version=version,
        subject_id=world.subject.id,
        config=cfg,
        index=0,
        text="Binary trees",
        unit_no=2,
        locator="page:7",
    )
    pg_session.commit()
    row = pg_session.get(ContentChunk, chunk.id)
    assert row.subject_id == world.subject.id and row.content_version_id == version.id
    assert (row.unit_no, row.source_file, row.locator, row.locator_type, row.chunk_type) == (
        2,
        version.original_filename,
        "page:7",
        LocatorType.PAGE,
        ContentType.NOTES,
    )
    assert row.embedding_config_id == cfg.id and len(row.text_sha256) == 64


def test_vector_1024_roundtrip_and_cosine_order(pg_session):
    world, _, version, cfg = _setup(pg_session)
    texts = ["arrays", "linked lists", "binary trees", "graph traversal"]
    for i, t in enumerate(texts):
        make_chunk(pg_session, version=version, subject_id=world.subject.id, config=cfg, index=i, text=t)
    pg_session.commit()
    query = FakeEmbedder.vector_for("binary trees")
    distance = ContentChunk.embedding.cosine_distance(query)
    rows = pg_session.execute(select(ContentChunk.text, distance).order_by(distance).limit(2)).all()
    assert rows[0][0] == "binary trees" and rows[0][1] == pytest.approx(0.0, abs=1e-6)
    assert rows[1][1] > rows[0][1]
    stored = pg_session.scalar(select(ContentChunk.embedding).where(ContentChunk.text == "arrays"))
    assert len(stored) == 1024 and stored[0] == pytest.approx(FakeEmbedder.vector_for("arrays")[0], abs=1e-5)


def test_wrong_dimension_vector_rejected_by_database(pg_session):
    world, _, version, cfg = _setup(pg_session)
    chunk = make_chunk(
        pg_session,
        version=version,
        subject_id=world.subject.id,
        config=cfg,
        index=0,
        text="x",
        embedded=False,
    )
    chunk.embedding = [0.1] * 768
    with pytest.raises((DataError, StatementError, IntegrityError), match="1024|dimension"):
        pg_session.flush()
    pg_session.rollback()


@pytest.mark.parametrize("locator", ["", "   "])
def test_null_or_empty_locator_rejected_by_check(pg_session, locator):
    world, _, version, cfg = _setup(pg_session)
    with pytest.raises(IntegrityError):
        make_chunk(
            pg_session,
            version=version,
            subject_id=world.subject.id,
            config=cfg,
            index=0,
            text="x",
            locator=locator,
        )
    pg_session.rollback()


def test_null_locator_rejected_by_not_null(pg_session):
    world, _, version, cfg = _setup(pg_session)
    with pytest.raises(IntegrityError, match="locator"):
        _insert_raw(pg_session, version=version, subject_id=world.subject.id, config=cfg, locator=None)


@pytest.mark.parametrize("token_count,ok", [(800, True), (801, False), (0, False)])
def test_token_count_must_be_between_1_and_800(pg_session, token_count, ok):
    world, _, version, cfg = _setup(pg_session)
    insert = lambda: _insert_raw(  # noqa: E731
        pg_session, version=version, subject_id=world.subject.id, config=cfg, token_count=token_count
    )
    if ok:
        insert()
    else:
        with pytest.raises(IntegrityError, match="ck_content_chunks_token_count"):
            insert()


def test_duplicate_chunk_index_within_version_rejected(pg_session):
    world, _, version, cfg = _setup(pg_session)
    make_chunk(pg_session, version=version, subject_id=world.subject.id, config=cfg, index=0, text="a")
    with pytest.raises(IntegrityError):
        make_chunk(pg_session, version=version, subject_id=world.subject.id, config=cfg, index=0, text="b")
    pg_session.rollback()


def test_chunk_type_check_rejects_unknown_value(pg_session):
    world, _, version, cfg = _setup(pg_session)
    with pytest.raises(IntegrityError, match="chunk_type"):
        _insert_raw(pg_session, version=version, subject_id=world.subject.id, config=cfg, chunk_type="BLOG")


def test_ingestion_repository_refuses_to_delete_chunks_of_approved_versions(pg_session):
    from app.services.ingestion_repository import SqlIngestionRepository

    world, _, version, cfg = _setup(pg_session)
    make_chunk(pg_session, version=version, subject_id=world.subject.id, config=cfg, index=0, text="a")
    version.status = ContentVersionStatus.ACTIVE
    version.ingestion_status = IngestionStatus.SUCCEEDED
    pg_session.commit()
    with pytest.raises(PermissionError):
        SqlIngestionRepository(pg_session, stale_after_seconds=2400).delete_chunks(str(version.id))
    assert pg_session.scalar(select(func.count()).select_from(ContentChunk)) == 1
