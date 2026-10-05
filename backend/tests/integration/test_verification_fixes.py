"""Fixes after the slice 2A verification (2026-10-04) on real PostgreSQL. Marker: pg.

M2 stale-RUNNING retry, m1 attempt locking, m2 Unit choice on upload, m3 resource_type CHECK,
m6 database-level chunk immutability, m7 link revision rules.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, inspect, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.config import settings
from app.core.errors import ConflictError
from app.models.content import (
    ApprovedResourceLink,
    ContentChunk,
    ContentVersion,
    ContentVersionStatus,
    IngestionStatus,
    LinkStatus,
)
from app.services import content_service
from app.services import resource_link_service as links
from app.services.ingestion.errors import IngestionInProgress
from app.services.ingestion_runtime import TIME_LIMIT_MESSAGE, repository
from tests.support.content_helpers import make_asset, make_chunk, make_embedding_config, make_version
from tests.support.fakes import FakeEmbedder, RecordingQueue
from tests.support.world import build_world, login

pytestmark = pytest.mark.pg

STALE = timedelta(seconds=settings.effective_ingest_stale_after_seconds + 60)
GOOD_LINK = dict(url="https://example.com/trees", title="Trees explained", resource_type="video")


def _draft_with_chunk(pg_session, *, embedded=True, status=ContentVersionStatus.DRAFT):
    world = build_world(pg_session)
    config = make_embedding_config(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    ingestion = IngestionStatus.SUCCEEDED if status != ContentVersionStatus.DRAFT else IngestionStatus.RUNNING
    version = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, status=status, ingestion=ingestion
    )
    chunk = make_chunk(
        pg_session,
        version=version,
        subject_id=world.subject.id,
        config=config,
        index=0,
        text="arrays are contiguous",
        embedded=embedded,
    )
    pg_session.flush()
    return world, version, chunk


# ---------------------------------------------------------------- migration 0002 additions


def test_migration_adds_heartbeat_column_resource_type_check_and_chunk_trigger(pg_session):
    insp = inspect(pg_session.connection())
    assert "ingestion_heartbeat_at" in {c["name"] for c in insp.get_columns("content_versions")}
    checks = {c["name"] for c in insp.get_check_constraints("approved_resource_links")}
    assert "ck_approved_resource_links_resource_type" in checks
    trigger = pg_session.execute(
        text("SELECT tgname FROM pg_trigger WHERE tgname = 'trg_content_chunks_guard'")
    ).scalar()
    assert trigger == "trg_content_chunks_guard"


def test_db_rejects_unknown_resource_type(pg_session):
    world = build_world(pg_session)
    with pytest.raises(IntegrityError), pg_session.begin_nested():
        pg_session.add(
            ApprovedResourceLink(
                subject_id=world.subject.id,
                url="https://example.com/x",
                title="x",
                resource_type="PODCAST",
                status=LinkStatus.DRAFT,
                uploaded_by=world.co.id,
            )
        )
        pg_session.flush()


# ---------------------------------------------------------------- m6 chunk immutability trigger


def test_trigger_allows_filling_a_null_embedding_on_a_draft(pg_session):
    _, version, chunk = _draft_with_chunk(pg_session, embedded=False)
    pg_session.execute(
        update(ContentChunk).where(ContentChunk.id == chunk.id).values(embedding=FakeEmbedder.vector_for("a"))
    )
    pg_session.flush()


def test_trigger_rejects_changing_chunk_text_even_on_a_draft(pg_session):
    _, _, chunk = _draft_with_chunk(pg_session)
    with pytest.raises(DBAPIError, match="only the embedding"), pg_session.begin_nested():
        pg_session.execute(update(ContentChunk).where(ContentChunk.id == chunk.id).values(text="changed"))


def test_trigger_rejects_replacing_a_stored_embedding(pg_session):
    _, _, chunk = _draft_with_chunk(pg_session, embedded=True)
    with pytest.raises(DBAPIError, match="cannot be replaced"), pg_session.begin_nested():
        pg_session.execute(
            update(ContentChunk)
            .where(ContentChunk.id == chunk.id)
            .values(embedding=FakeEmbedder.vector_for("other"))
        )


@pytest.mark.parametrize("status", [ContentVersionStatus.ACTIVE, ContentVersionStatus.SUPERSEDED])
def test_trigger_rejects_update_and_delete_of_approved_chunks(pg_session, status):
    _, _, chunk = _draft_with_chunk(pg_session, status=status)
    with pytest.raises(DBAPIError, match="immutable"), pg_session.begin_nested():
        pg_session.execute(update(ContentChunk).where(ContentChunk.id == chunk.id).values(page_no=2))
    with pytest.raises(DBAPIError, match="immutable"), pg_session.begin_nested():
        pg_session.execute(delete(ContentChunk).where(ContentChunk.id == chunk.id))


def test_repository_refuses_embeddings_for_an_approved_version(pg_session):
    _, version, chunk = _draft_with_chunk(pg_session, status=ContentVersionStatus.ACTIVE)
    with pytest.raises(PermissionError):
        repository(pg_session).set_embeddings(str(version.id), {str(chunk.id): [0.0] * 1024})


# ---------------------------------------------------------------- m1 / M2 attempts and retry


def test_begin_attempt_refuses_a_live_running_version(pg_session):
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.RUNNING
    )
    pg_session.commit()
    with pytest.raises(IngestionInProgress):
        repository(pg_session).begin_attempt(str(version.id))


def test_begin_attempt_takes_over_a_stale_running_version(pg_session):
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(
        pg_session,
        asset=asset,
        actor=world.co,
        version_no=1,
        ingestion=IngestionStatus.RUNNING,
        heartbeat_at=datetime.now(UTC) - STALE,
    )
    pg_session.commit()
    attempt = repository(pg_session).begin_attempt(str(version.id))
    pg_session.refresh(version)
    assert attempt == 1 and version.ingestion_status == IngestionStatus.RUNNING
    assert version.ingestion_heartbeat_at > datetime.now(UTC) - timedelta(minutes=1)


def test_retry_of_a_stale_running_version_is_allowed_and_audited(pg_session):
    world, queue = build_world(pg_session), RecordingQueue()
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(
        pg_session,
        asset=asset,
        actor=world.co,
        version_no=1,
        ingestion=IngestionStatus.RUNNING,
        heartbeat_at=datetime.now(UTC) - STALE,
    )
    pg_session.commit()
    content_service.retry_ingestion(pg_session, actor=world.co, version_id=version.id, queue=queue)
    assert version.ingestion_status == IngestionStatus.PENDING and queue.enqueued == [str(version.id)]


def test_retry_of_a_pending_version_is_allowed(pg_session):
    world, queue = build_world(pg_session), RecordingQueue()
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.PENDING
    )
    pg_session.commit()
    content_service.retry_ingestion(pg_session, actor=world.co, version_id=version.id, queue=queue)
    assert queue.enqueued == [str(version.id)]


def test_retry_of_a_live_running_version_says_when_it_becomes_possible(pg_session):
    world, queue = build_world(pg_session), RecordingQueue()
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.RUNNING
    )
    pg_session.commit()
    with pytest.raises(ConflictError, match="retry after"):
        content_service.retry_ingestion(pg_session, actor=world.co, version_id=version.id, queue=queue)


def test_version_response_reports_retry_availability(pg_client, pg_session):
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    live = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.RUNNING
    )
    stale = make_version(
        pg_session,
        asset=asset,
        actor=world.co,
        version_no=2,
        ingestion=IngestionStatus.RUNNING,
        heartbeat_at=datetime.now(UTC) - STALE,
    )
    pg_session.commit()
    headers = login(pg_client, world.co)
    live_body = pg_client.get(f"/teacher/content/versions/{live.id}", headers=headers).json()
    stale_body = pg_client.get(f"/teacher/content/versions/{stale.id}", headers=headers).json()
    assert live_body["can_retry"] is False and live_body["retry_available_at"] is not None
    assert stale_body["can_retry"] is True


def test_time_limit_failure_marks_the_running_stage_failed(pg_session):
    from app.services.ingestion_runtime import mark_timed_out

    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.PENDING
    )
    pg_session.commit()
    repo = repository(pg_session)
    attempt = repo.begin_attempt(str(version.id))
    now = datetime.now(UTC)
    repo.record_stage(str(version.id), "OCR", attempt, "RUNNING", now, None, None, None)
    mark_timed_out(pg_session, version.id)
    pg_session.refresh(version)
    assert version.ingestion_status == IngestionStatus.FAILED
    assert (version.failed_stage, version.failure_message) == ("OCR", TIME_LIMIT_MESSAGE)


# ---------------------------------------------------------------- m2 Unit choice on upload (API)


@pytest.mark.minio
@pytest.mark.parametrize(
    "form,status",
    [
        ({"content_type": "NOTES"}, 400),
        ({"content_type": "NOTES", "all_units": "true", "unit_id": "UNIT"}, 400),
        ({"content_type": "NOTES", "all_units": "true"}, 201),
        ({"content_type": "NOTES", "unit_id": "UNIT"}, 201),
        ({"content_type": "SYLLABUS"}, 201),
        ({"content_type": "SYLLABUS", "unit_id": "UNIT"}, 400),
    ],
)
def test_upload_requires_a_unit_or_all_units_for_non_syllabus(
    pg_minio_client, pg_session, minio_cleanup, form, status
):
    from tests.support import docs

    world = build_world(pg_session)
    headers = login(pg_minio_client, world.co)
    data = {"title": "Notes", **form}
    if data.get("unit_id") == "UNIT":
        data["unit_id"] = str(world.units[0].id)
    resp = pg_minio_client.post(
        f"/teacher/subjects/{world.subject.id}/content/uploads",
        headers=headers,
        files={"file": ("notes.txt", docs.make_txt("Unit 1\nArrays."), "text/plain")},
        data=data,
    )
    assert resp.status_code == status, resp.text
    if status == 201:
        version = pg_session.get(ContentVersion, uuid.UUID(resp.json()["id"]))
        minio_cleanup.append(version.storage_key)


# ---------------------------------------------------------------- m7 link revisions


def test_a_draft_link_cannot_be_revised(pg_session):
    world = build_world(pg_session)
    draft = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD_LINK)
    with pytest.raises(ConflictError, match="Only an approved link"):
        links.create_revision(pg_session, actor=world.co, link_id=draft.id, **GOOD_LINK)


def test_second_revision_of_the_same_link_cannot_also_be_approved(pg_session):
    world = build_world(pg_session)
    first = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD_LINK)
    links.approve_link(pg_session, actor=world.owner, link_id=first.id, reason=None)
    rev_a = links.create_revision(pg_session, actor=world.co, link_id=first.id, **GOOD_LINK)
    rev_b = links.create_revision(pg_session, actor=world.co, link_id=first.id, **GOOD_LINK)
    links.approve_link(pg_session, actor=world.owner, link_id=rev_a.id, reason=None)
    with pytest.raises(ConflictError, match="no longer the approved one"):
        links.approve_link(pg_session, actor=world.owner, link_id=rev_b.id, reason=None)
    assert (first.status, rev_a.status, rev_b.status) == (
        LinkStatus.SUPERSEDED,
        LinkStatus.APPROVED,
        LinkStatus.DRAFT,
    )


# ---------------------------------------------------------------- m5 / N8 denied-access logging


DENIAL_LOGGER = "app.services.content_service"


def _denials(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == DENIAL_LOGGER]


def test_unassigned_rollback_is_logged(pg_session, caplog):
    import logging

    from app.core.errors import NotFoundError

    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    pg_session.commit()
    with caplog.at_level(logging.WARNING, logger=DENIAL_LOGGER), pytest.raises(NotFoundError):
        content_service.rollback_asset(
            pg_session, actor=world.outsider, asset_id=asset.id, target_version_id=uuid.uuid4(), reason=None
        )
    assert any("asset_not_assigned_or_missing" in m and str(asset.id) in m for m in _denials(caplog))


def test_missing_chunk_lookup_is_logged(pg_session, caplog):
    import logging

    from app.core.errors import NotFoundError

    world = build_world(pg_session)
    missing = uuid.uuid4()
    with caplog.at_level(logging.WARNING, logger=DENIAL_LOGGER), pytest.raises(NotFoundError):
        content_service.resolve_chunk(pg_session, world.co, missing)
    assert any("chunk_missing" in m and str(missing) in m for m in _denials(caplog))


def test_unassigned_link_access_is_logged(pg_session, caplog):
    import logging

    from app.core.errors import NotFoundError

    world = build_world(pg_session)
    link = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD_LINK)
    with caplog.at_level(logging.WARNING, logger=DENIAL_LOGGER), pytest.raises(NotFoundError):
        links.approve_link(pg_session, actor=world.outsider, link_id=link.id, reason=None)
    assert any("link_not_assigned_or_missing" in m and str(link.id) in m for m in _denials(caplog))


def test_co_teacher_activation_denial_is_logged(pg_session, caplog):
    import logging

    from app.core.errors import ForbiddenError

    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(pg_session, asset=asset, actor=world.co, version_no=1)
    pg_session.commit()
    with caplog.at_level(logging.WARNING, logger=DENIAL_LOGGER), pytest.raises(ForbiddenError):
        content_service.activate_version(pg_session, actor=world.co, version_id=version.id, reason=None)
    assert any("not_subject_owner" in m for m in _denials(caplog))
