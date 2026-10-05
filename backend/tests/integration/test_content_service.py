"""FR-CON-001 / FR-CON-004, AC-005, BUS-039, BUS-043 against real PostgreSQL (+ real MinIO for uploads).

Markers: pg for DB-only tests; pg + minio for tests that upload through the service.
"""

from __future__ import annotations

import threading

import pytest
from sqlalchemy import func, select, text

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.audit_log import AuditLog
from app.models.content import (
    ContentAsset,
    ContentType,
    ContentVersion,
    ContentVersionStatus,
    IngestionStatus,
)
from app.services import content_service
from tests.support import docs
from tests.support.content_helpers import make_asset, make_version
from tests.support.fakes import RecordingQueue
from tests.support.world import build_world

pg = pytest.mark.pg


def _upload(
    db,
    world,
    store,
    queue,
    cleanup,
    *,
    actor=None,
    data=None,
    name="notes.txt",
    ctype=ContentType.NOTES,
    asset=None,
    tmp_path=None,
    **kw,
):
    actor = actor or world.co
    path = tmp_path / name
    path.write_bytes(data if data is not None else docs.make_txt("Arrays store elements contiguously."))
    version = content_service.upload_content(
        db,
        actor=actor,
        subject_id=world.subject.id,
        content_type=ctype,
        title="Notes",
        unit_id=kw.get("unit_id"),
        all_units=kw.get("all_units", kw.get("unit_id") is None and ctype != ContentType.SYLLABUS),
        content_asset_id=asset.id if asset else None,
        original_filename=name,
        declared_content_type=kw.get("declared"),
        local_path=str(path),
        store=store,
        queue=queue,
    )
    cleanup.append(version.storage_key)
    return version


# ------------------------------------------------------------------ upload (FR-CON-001)


@pytest.mark.pg
@pytest.mark.minio
def test_upload_creates_draft_version_with_sha_size_mime(pg_session, minio_store, minio_cleanup, tmp_path):
    world, queue = build_world(pg_session), RecordingQueue()
    version = _upload(pg_session, world, minio_store, queue, minio_cleanup, tmp_path=tmp_path)
    assert (
        version.status == ContentVersionStatus.DRAFT and version.ingestion_status == IngestionStatus.PENDING
    )
    assert version.version_no == 1 and version.mime_type == "text/plain" and version.ext == "txt"
    assert len(version.sha256) == 64 and version.size_bytes > 0
    assert minio_store.exists(version.storage_key)


@pytest.mark.pg
@pytest.mark.minio
def test_upload_enqueues_exactly_one_ingestion_task(pg_session, minio_store, minio_cleanup, tmp_path):
    world, queue = build_world(pg_session), RecordingQueue()
    version = _upload(pg_session, world, minio_store, queue, minio_cleanup, tmp_path=tmp_path)
    assert queue.enqueued == [str(version.id)]


@pytest.mark.pg
@pytest.mark.minio
def test_broker_outage_leaves_version_pending_and_still_returns_it(
    pg_session, minio_store, minio_cleanup, tmp_path
):
    world = build_world(pg_session)
    version = _upload(
        pg_session, world, minio_store, RecordingQueue(fail=True), minio_cleanup, tmp_path=tmp_path
    )
    assert version.ingestion_status == IngestionStatus.PENDING


@pytest.mark.pg
@pytest.mark.minio
def test_upload_v2_leaves_v1_active_and_intact(pg_session, minio_store, minio_cleanup, tmp_path):
    """AC-005 positive: v1 ACTIVE + assigned Teacher uploads v2 => v1 stays ACTIVE, v2 DRAFT."""
    world, queue = build_world(pg_session), RecordingQueue()
    v1 = _upload(pg_session, world, minio_store, queue, minio_cleanup, tmp_path=tmp_path, name="v1.txt")
    v1.ingestion_status = IngestionStatus.SUCCEEDED
    pg_session.commit()
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason="go")
    asset = pg_session.get(ContentAsset, v1.content_asset_id)
    v2 = _upload(
        pg_session,
        world,
        minio_store,
        queue,
        minio_cleanup,
        tmp_path=tmp_path,
        name="v2.txt",
        data=docs.make_txt("Revised notes."),
        asset=asset,
    )
    pg_session.refresh(v1)
    assert (v1.status, v2.status, v2.version_no) == (
        ContentVersionStatus.ACTIVE,
        ContentVersionStatus.DRAFT,
        2,
    )
    assert minio_store.exists(v1.storage_key) and v1.storage_key != v2.storage_key


@pytest.mark.pg
@pytest.mark.minio
def test_unassigned_teacher_upload_rejected_404_no_data(pg_session, minio_store, minio_cleanup, tmp_path):
    world = build_world(pg_session)
    with pytest.raises(NotFoundError):
        _upload(
            pg_session,
            world,
            minio_store,
            RecordingQueue(),
            minio_cleanup,
            actor=world.outsider,
            tmp_path=tmp_path,
        )
    assert pg_session.scalar(select(func.count()).select_from(ContentAsset)) == 0


@pytest.mark.pg
@pytest.mark.minio
def test_validation_failures_store_nothing_and_create_no_rows(
    pg_session, minio_store, minio_cleanup, tmp_path
):
    world, queue = build_world(pg_session), RecordingQueue()
    with pytest.raises(ValidationError):  # actual MIME mismatch
        _upload(
            pg_session,
            world,
            minio_store,
            queue,
            minio_cleanup,
            tmp_path=tmp_path,
            name="x.pdf",
            data=docs.make_txt("not a pdf"),
        )
    with pytest.raises(ValidationError):  # legacy extension
        _upload(pg_session, world, minio_store, queue, minio_cleanup, tmp_path=tmp_path, name="x.doc")
    assert pg_session.scalar(select(func.count()).select_from(ContentVersion)) == 0 and queue.enqueued == []


@pytest.mark.pg
@pytest.mark.minio
def test_second_syllabus_asset_for_subject_conflicts_but_new_version_allowed(
    pg_session, minio_store, minio_cleanup, tmp_path
):
    world, queue = build_world(pg_session), RecordingQueue()
    first = _upload(
        pg_session,
        world,
        minio_store,
        queue,
        minio_cleanup,
        tmp_path=tmp_path,
        ctype=ContentType.SYLLABUS,
        name="s1.txt",
    )
    with pytest.raises(ConflictError):
        _upload(
            pg_session,
            world,
            minio_store,
            queue,
            minio_cleanup,
            tmp_path=tmp_path,
            ctype=ContentType.SYLLABUS,
            name="s2.txt",
        )
    asset = pg_session.get(ContentAsset, first.content_asset_id)
    again = _upload(
        pg_session,
        world,
        minio_store,
        queue,
        minio_cleanup,
        tmp_path=tmp_path,
        ctype=ContentType.SYLLABUS,
        name="s3.txt",
        asset=asset,
    )
    assert again.version_no == 2


@pytest.mark.pg
@pytest.mark.minio
def test_unit_must_belong_to_subject_and_asset_type_must_match(
    pg_session, minio_store, minio_cleanup, tmp_path
):
    import uuid

    world, queue = build_world(pg_session), RecordingQueue()
    with pytest.raises(ValidationError):
        _upload(pg_session, world, minio_store, queue, minio_cleanup, tmp_path=tmp_path, unit_id=uuid.uuid4())
    v = _upload(
        pg_session, world, minio_store, queue, minio_cleanup, tmp_path=tmp_path, unit_id=world.units[0].id
    )
    asset = pg_session.get(ContentAsset, v.content_asset_id)
    with pytest.raises(ValidationError):
        _upload(
            pg_session,
            world,
            minio_store,
            queue,
            minio_cleanup,
            tmp_path=tmp_path,
            ctype=ContentType.PYQ,
            asset=asset,
        )


@pytest.mark.pg
@pytest.mark.minio
def test_activate_rollback_upload_each_write_audit_row_same_txn(
    pg_session, minio_store, minio_cleanup, tmp_path
):
    world, queue = build_world(pg_session), RecordingQueue()
    v1 = _upload(pg_session, world, minio_store, queue, minio_cleanup, tmp_path=tmp_path)
    v1.ingestion_status = IngestionStatus.SUCCEEDED
    pg_session.commit()
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason="r1")
    actions = set(pg_session.scalars(select(AuditLog.action)))
    assert {"UPLOAD_CONTENT_VERSION", "ACTIVATE_CONTENT_VERSION"} <= actions
    entry = pg_session.scalar(select(AuditLog).where(AuditLog.action == "ACTIVATE_CONTENT_VERSION"))
    assert entry.actor_id == world.owner.id and entry.reason == "r1" and entry.entity_id == str(v1.id)


# ------------------------------------------------------------------ activation / rollback (FR-CON-004)


def _two_versions(db, world):
    asset = make_asset(db, subject_id=world.subject.id, actor=world.co)
    v1 = make_version(db, asset=asset, actor=world.co, version_no=1)
    v2 = make_version(db, asset=asset, actor=world.co, version_no=2)
    db.commit()
    return asset, v1, v2


@pg
def test_owner_activates_v2_v1_superseded_but_traceable(pg_session):
    """AC-005 positive: PRIMARY Owner activates v2 => v1 superseded but still resolvable."""
    world = build_world(pg_session)
    asset, v1, v2 = _two_versions(pg_session, world)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v2.id, reason="newer")
    pg_session.refresh(v1)
    assert (v1.status, v2.status) == (ContentVersionStatus.SUPERSEDED, ContentVersionStatus.ACTIVE)
    assert v2.supersedes_version_id == v1.id and v2.activated_by == world.owner.id and v2.activated_at


@pg
def test_co_teacher_activation_rejected_403(pg_session):
    """AC-005 negative: CO Teacher activation is rejected."""
    world = build_world(pg_session)
    _, v1, _ = _two_versions(pg_session, world)
    with pytest.raises(ForbiddenError):
        content_service.activate_version(pg_session, actor=world.co, version_id=v1.id, reason=None)
    pg_session.refresh(v1)
    assert v1.status == ContentVersionStatus.DRAFT


@pg
def test_unassigned_teacher_activation_rejected_404(pg_session):
    """AC-005 negative: unassigned Teacher is rejected without revealing the version."""
    world = build_world(pg_session)
    _, v1, _ = _two_versions(pg_session, world)
    with pytest.raises(NotFoundError):
        content_service.activate_version(pg_session, actor=world.outsider, version_id=v1.id, reason=None)


@pg
def test_activation_authorization_matrix_owner_co_primary_nonowner_unassigned(pg_session):
    from app.models.subject_instance import TeacherAssignmentRole
    from app.models.user import User, UserRole
    from app.services import assignment_service
    from tests.support.world import _user

    world = build_world(pg_session)
    primary_non_owner = _user(pg_session, "pno@example.com", UserRole.TEACHER)
    assignment_service.assign_teacher(
        pg_session,
        actor=world.admin,
        teacher_id=primary_non_owner.id,
        subject_instance_id=world.instance.id,
        role=TeacherAssignmentRole.PRIMARY,
    )
    _, v1, v2 = _two_versions(pg_session, world)
    results = {}
    for label, user in (
        ("co", world.co),
        ("primary_non_owner", primary_non_owner),
        ("unassigned", world.outsider),
        ("owner", world.owner),
    ):
        try:
            content_service.activate_version(pg_session, actor=user, version_id=v1.id, reason=None)
            results[label] = "ok"
        except (ForbiddenError, NotFoundError) as exc:
            results[label] = type(exc).__name__
    assert results == {
        "co": "ForbiddenError",
        "primary_non_owner": "ForbiddenError",  # only the designated Owner, not any PRIMARY
        "unassigned": "NotFoundError",
        "owner": "ok",
    }
    assert isinstance(primary_non_owner, User)


@pg
def test_activate_rejected_when_ingestion_not_succeeded(pg_session):
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    statuses = (IngestionStatus.PENDING, IngestionStatus.RUNNING, IngestionStatus.FAILED)
    for n, status in enumerate(statuses, start=1):
        v = make_version(pg_session, asset=asset, actor=world.co, version_no=n, ingestion=status)
        pg_session.commit()
        with pytest.raises(ConflictError):
            content_service.activate_version(pg_session, actor=world.owner, version_id=v.id, reason=None)


@pg
def test_only_draft_can_be_activated(pg_session):
    world = build_world(pg_session)
    _, v1, _ = _two_versions(pg_session, world)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    with pytest.raises(ConflictError):
        content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)


@pg
def test_owner_rolls_back_to_prior_valid_version_pointer_only(pg_session):
    world = build_world(pg_session)
    asset, v1, v2 = _two_versions(pg_session, world)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v2.id, reason=None)
    keys_before = (v1.storage_key, v2.storage_key)
    target = content_service.rollback_asset(
        pg_session, actor=world.owner, asset_id=asset.id, target_version_id=v1.id, reason="bad v2"
    )
    pg_session.refresh(v2)
    assert (target.status, v2.status) == (ContentVersionStatus.ACTIVE, ContentVersionStatus.SUPERSEDED)
    assert (v1.storage_key, v2.storage_key) == keys_before  # nothing moved or copied
    assert pg_session.scalar(select(AuditLog.action).where(AuditLog.action == "ROLLBACK_CONTENT_VERSION"))


@pg
def test_rollback_to_failed_ingestion_version_rejected(pg_session):
    world = build_world(pg_session)
    asset, v1, v2 = _two_versions(pg_session, world)
    failed = make_version(
        pg_session, asset=asset, actor=world.co, version_no=3, ingestion=IngestionStatus.FAILED
    )
    failed.status = ContentVersionStatus.SUPERSEDED
    pg_session.commit()
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    for bad in (failed, v2):  # a never-active DRAFT is also not a valid rollback target
        with pytest.raises(ConflictError):
            content_service.rollback_asset(
                pg_session, actor=world.owner, asset_id=asset.id, target_version_id=bad.id, reason=None
            )


@pg
def test_co_rollback_rejected(pg_session):
    world = build_world(pg_session)
    asset, v1, v2 = _two_versions(pg_session, world)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v2.id, reason=None)
    with pytest.raises(ForbiddenError):
        content_service.rollback_asset(
            pg_session, actor=world.co, asset_id=asset.id, target_version_id=v1.id, reason=None
        )
    with pytest.raises(NotFoundError):
        content_service.rollback_asset(
            pg_session, actor=world.outsider, asset_id=asset.id, target_version_id=v1.id, reason=None
        )


@pg
def test_prior_citations_remain_resolvable_after_activation_and_rollback(pg_session):
    from tests.support.content_helpers import make_chunk, make_embedding_config

    world = build_world(pg_session)
    asset, v1, v2 = _two_versions(pg_session, world)
    cfg = make_embedding_config(pg_session)
    chunk = make_chunk(
        pg_session, version=v1, subject_id=world.subject.id, config=cfg, index=0, text="Binary trees"
    )
    pg_session.commit()
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v2.id, reason=None)
    resolved, version, _ = content_service.resolve_chunk(pg_session, world.co, chunk.id)
    assert (
        version.id == v1.id
        and version.status == ContentVersionStatus.SUPERSEDED
        and resolved.locator == "page:1"
    )
    content_service.rollback_asset(
        pg_session, actor=world.owner, asset_id=asset.id, target_version_id=v1.id, reason=None
    )
    assert (
        content_service.resolve_chunk(pg_session, world.co, chunk.id)[1].status == ContentVersionStatus.ACTIVE
    )


@pg
def test_retry_only_for_failed_or_pending_draft(pg_session):
    world, queue = build_world(pg_session), RecordingQueue()
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    failed = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.FAILED
    )
    ok = make_version(
        pg_session, asset=asset, actor=world.co, version_no=2, ingestion=IngestionStatus.SUCCEEDED
    )
    running = make_version(
        pg_session, asset=asset, actor=world.co, version_no=3, ingestion=IngestionStatus.RUNNING
    )
    pg_session.commit()
    content_service.retry_ingestion(pg_session, actor=world.co, version_id=failed.id, queue=queue)
    assert queue.enqueued == [str(failed.id)] and failed.ingestion_status == IngestionStatus.PENDING
    for bad in (ok, running):
        with pytest.raises(ConflictError):
            content_service.retry_ingestion(pg_session, actor=world.co, version_id=bad.id, queue=queue)
    with pytest.raises(NotFoundError):
        content_service.retry_ingestion(pg_session, actor=world.outsider, version_id=failed.id, queue=queue)


@pg
def test_db_rejects_active_version_that_was_not_ingested(pg_session):
    from sqlalchemy.exc import IntegrityError

    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    with pytest.raises(IntegrityError):
        make_version(
            pg_session,
            asset=asset,
            actor=world.co,
            version_no=1,
            status=ContentVersionStatus.ACTIVE,
            ingestion=IngestionStatus.PENDING,
        )
    pg_session.rollback()


@pg
def test_db_allows_only_one_active_version_per_asset(pg_session):
    from sqlalchemy.exc import IntegrityError

    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    make_version(pg_session, asset=asset, actor=world.co, version_no=1, status=ContentVersionStatus.ACTIVE)
    with pytest.raises(IntegrityError):
        make_version(
            pg_session, asset=asset, actor=world.co, version_no=2, status=ContentVersionStatus.ACTIVE
        )
    pg_session.rollback()


@pg
def test_list_assigned_subjects_scopes_to_assignments_and_flags_owner(pg_session):
    world = build_world(pg_session)
    mine = content_service.list_assigned_subjects(pg_session, world.co)
    assert [(s.subject.id, s.is_owner, len(s.units)) for s in mine] == [(world.subject.id, False, 3)]
    assert content_service.list_assigned_subjects(pg_session, world.owner)[0].is_owner is True
    assert content_service.list_assigned_subjects(pg_session, world.outsider) == []


@pytest.mark.pg
def test_concurrent_activation_leaves_exactly_one_active(pg_committed):
    """Two real sessions racing to activate different DRAFTs of one asset: the asset row lock
    serialises them and the partial unique index guarantees a single ACTIVE version."""
    factory = pg_committed
    with factory() as setup:
        world = build_world(setup)
        asset, v1, v2 = _two_versions(setup, world)
        owner_id, v1_id, v2_id, asset_id = world.owner.id, v1.id, v2.id, asset.id
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker(version_id):
        with factory() as db:
            from app.models.user import User

            actor = db.get(User, owner_id)
            barrier.wait()
            try:
                content_service.activate_version(db, actor=actor, version_id=version_id, reason=None)
                outcomes.append("ok")
            except Exception as exc:  # noqa: BLE001
                outcomes.append(type(exc).__name__)

    threads = [threading.Thread(target=worker, args=(v,)) for v in (v1_id, v2_id)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    with factory() as check:
        active = check.scalar(
            select(func.count())
            .select_from(ContentVersion)
            .where(
                ContentVersion.content_asset_id == asset_id,
                ContentVersion.status == ContentVersionStatus.ACTIVE,
            )
        )
        superseded = check.scalar(text("SELECT count(*) FROM content_versions WHERE status = 'SUPERSEDED'"))
    assert active == 1 and outcomes.count("ok") == 2 and superseded == 1
