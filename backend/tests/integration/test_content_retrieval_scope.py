"""FR-CON-002 Post: chunks retrievable only under correct subject/version/approval scope. Marker: pg."""

from __future__ import annotations

import pytest

from app.models.content import ContentVersionStatus, IngestionStatus
from app.services import content_retrieval, content_service
from tests.support.content_helpers import make_asset, make_chunk, make_embedding_config, make_version
from tests.support.fakes import FakeEmbedder
from tests.support.world import build_world

pytestmark = pytest.mark.pg

Q = FakeEmbedder.vector_for("binary trees")


def _active_version_with_chunk(
    db,
    world,
    cfg,
    *,
    text="binary trees",
    subject_id=None,
    status=ContentVersionStatus.ACTIVE,
    ingestion=IngestionStatus.SUCCEEDED,
    embedded=True,
    version_no=1,
    asset=None,
):
    asset = asset or make_asset(db, subject_id=subject_id or world.subject.id, actor=world.co)
    version = make_version(
        db, asset=asset, actor=world.co, version_no=version_no, status=status, ingestion=ingestion
    )
    chunk = make_chunk(
        db, version=version, subject_id=asset.subject_id, config=cfg, index=0, text=text, embedded=embedded
    )
    db.commit()
    return asset, version, chunk


def _ids(db, world, cfg, **kw):
    return [
        c.id
        for c, _ in content_retrieval.retrieve_approved_chunks(
            db,
            subject_id=kw.get("subject_id", world.subject.id),
            query_embedding=Q,
            embedding_config_id=cfg.id,
        )
    ]


def test_active_version_chunks_are_retrievable_nearest_first(pg_session):
    world, cfg = build_world(pg_session), None
    cfg = make_embedding_config(pg_session)
    asset, version, near = _active_version_with_chunk(pg_session, world, cfg)
    far = make_chunk(
        pg_session,
        version=version,
        subject_id=world.subject.id,
        config=cfg,
        index=1,
        text="completely different",
    )
    pg_session.commit()
    results = content_retrieval.retrieve_approved_chunks(
        pg_session, subject_id=world.subject.id, query_embedding=Q, embedding_config_id=cfg.id, limit=5
    )
    assert [c.id for c, _ in results] == [near.id, far.id] and results[0][1] == pytest.approx(0.0, abs=1e-6)


def test_draft_version_chunks_excluded_from_approved_scope(pg_session):
    world, cfg = build_world(pg_session), make_embedding_config(pg_session)
    _active_version_with_chunk(pg_session, world, cfg, status=ContentVersionStatus.DRAFT)
    assert _ids(pg_session, world, cfg) == []


def test_failed_or_running_ingestion_chunks_excluded(pg_session):
    world, cfg = build_world(pg_session), make_embedding_config(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    for n, ing in enumerate((IngestionStatus.FAILED, IngestionStatus.RUNNING), start=1):
        v = make_version(
            pg_session,
            asset=asset,
            actor=world.co,
            version_no=n,
            status=ContentVersionStatus.DRAFT,
            ingestion=ing,
        )
        make_chunk(
            pg_session, version=v, subject_id=asset.subject_id, config=cfg, index=0, text="binary trees"
        )
    pg_session.commit()
    assert _ids(pg_session, world, cfg) == []


def test_other_subject_chunks_never_returned(pg_session):
    world_a, world_b = build_world(pg_session, tag="a"), build_world(pg_session, tag="b")
    cfg = make_embedding_config(pg_session)
    _active_version_with_chunk(pg_session, world_b, cfg)
    assert _ids(pg_session, world_a, cfg) == []
    assert len(_ids(pg_session, world_b, cfg)) == 1


def test_superseded_chunks_not_in_active_scope_but_resolvable_by_id(pg_session):
    world, cfg = build_world(pg_session), make_embedding_config(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    v1 = make_version(pg_session, asset=asset, actor=world.co, version_no=1)
    v2 = make_version(pg_session, asset=asset, actor=world.co, version_no=2)
    old = make_chunk(
        pg_session, version=v1, subject_id=world.subject.id, config=cfg, index=0, text="old binary trees"
    )
    pg_session.commit()
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v2.id, reason=None)
    assert old.id not in _ids(pg_session, world, cfg)
    chunk, version, _ = content_service.resolve_chunk(pg_session, world.co, old.id)
    assert chunk.id == old.id and version.status == ContentVersionStatus.SUPERSEDED


def test_embedding_config_mismatch_not_compared(pg_session):
    world = build_world(pg_session)
    cfg_a, cfg_b = make_embedding_config(pg_session), make_embedding_config(pg_session)
    _active_version_with_chunk(pg_session, world, cfg_a)
    assert _ids(pg_session, world, cfg_b) == []
    assert len(_ids(pg_session, world, cfg_a)) == 1


def test_unembedded_chunks_never_returned(pg_session):
    world, cfg = build_world(pg_session), make_embedding_config(pg_session)
    _active_version_with_chunk(pg_session, world, cfg, embedded=False)
    assert _ids(pg_session, world, cfg) == []


def test_unit_filter_applies(pg_session):
    world, cfg = build_world(pg_session), make_embedding_config(pg_session)
    asset, version, _ = _active_version_with_chunk(pg_session, world, cfg)
    make_chunk(
        pg_session,
        version=version,
        subject_id=world.subject.id,
        config=cfg,
        index=1,
        text="graphs",
        unit_no=3,
    )
    pg_session.commit()
    res = content_retrieval.retrieve_approved_chunks(
        pg_session, subject_id=world.subject.id, query_embedding=Q, embedding_config_id=cfg.id, unit_no=3
    )
    assert [c.unit_no for c, _ in res] == [3]


def test_chunks_for_version_returns_ordered_chunks_of_that_version_only(pg_session):
    world, cfg = build_world(pg_session), make_embedding_config(pg_session)
    _, v, c0 = _active_version_with_chunk(pg_session, world, cfg)
    _, _, _ = _active_version_with_chunk(pg_session, world, cfg, text="other")
    got = content_retrieval.chunks_for_version(
        pg_session, subject_id=world.subject.id, content_version_id=v.id
    )
    assert [c.id for c in got] == [c0.id]
