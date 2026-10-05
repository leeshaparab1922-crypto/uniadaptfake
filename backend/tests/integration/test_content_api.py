"""Teacher content API (C1..C13) on real PostgreSQL + real MinIO. FR-CON-001..004, AC-004, AC-005.

Markers: pg + minio for upload tests (pg_minio_client); pg only where object storage is not touched.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models.content import ContentChunk, ContentVersion, IngestionStatus
from app.models.user import UserRole
from tests.support import docs
from tests.support.content_helpers import make_asset, make_chunk, make_embedding_config, make_version
from tests.support.world import _user, build_world, login

pytestmark = pytest.mark.pg

UPLOADS = {
    "pdf": (
        "notes.pdf",
        lambda: docs.make_text_pdf([["Unit 1 arrays are contiguous collections of items."]]),
        "application/pdf",
    ),
    "pptx": ("notes.pptx", lambda: docs.make_pptx([("Arrays", "notes")]), None),
    "docx": ("notes.docx", lambda: docs.make_docx([("Heading 1", "Unit 1"), ("Normal", "Arrays")]), None),
    "txt": ("notes.txt", lambda: docs.make_txt("Arrays are contiguous."), "text/plain"),
}


def _upload(client, headers, world, *, name="notes.txt", data=None, mime=None, **form):
    fields = {"content_type": "NOTES", "title": "Notes", **form}
    if fields["content_type"] != "SYLLABUS" and fields.get("unit_id") is None and "all_units" not in fields:
        fields["all_units"] = "true"  # finding m2: non-syllabus uploads name a Unit or "All units"
    return client.post(
        f"/teacher/subjects/{world.subject.id}/content/uploads",
        headers=headers,
        files={
            "file": (
                name,
                data if data is not None else docs.make_txt("hi there"),
                mime or "application/octet-stream",
            )
        },
        data={k: str(v) for k, v in fields.items() if v is not None},
    )


def _track(pg_session, minio_cleanup):
    for key in pg_session.scalars(select(ContentVersion.storage_key)):
        if key not in minio_cleanup:
            minio_cleanup.append(key)


# ------------------------------------------------------------------ C1


def test_c1_lists_only_assigned_subjects_with_owner_flag(pg_client, pg_session):
    world = build_world(pg_session)
    headers = login(pg_client, world.co)
    body = pg_client.get("/teacher/subjects", headers=headers).json()
    assert [(s["id"], s["is_owner"], len(s["units"])) for s in body] == [(str(world.subject.id), False, 3)]
    login(pg_client, world.owner)
    assert pg_client.get("/teacher/subjects").json()[0]["is_owner"] is True
    login(pg_client, world.outsider)
    assert pg_client.get("/teacher/subjects").json() == []


@pytest.mark.parametrize("role", [UserRole.STUDENT, UserRole.ADMIN])
def test_non_teacher_roles_forbidden(pg_client, pg_session, role):
    world = build_world(pg_session)
    # Lower case: login looks emails up in lower case (Phase 1 auth_service.authenticate).
    other = _user(pg_session, f"x-{role.value.lower()}@example.com", role)
    pg_session.commit()
    headers = login(pg_client, other)
    assert pg_client.get("/teacher/subjects").status_code == 403
    assert pg_client.get(f"/teacher/subjects/{world.subject.id}/content/assets").status_code == 403
    assert _upload(pg_client, headers, world).status_code == 403


def test_unauthenticated_and_missing_csrf_rejected(pg_client, pg_session):
    world = build_world(pg_session)
    assert pg_client.get("/teacher/subjects").status_code == 401
    login(pg_client, world.co)
    assert _upload(pg_client, {}, world).status_code == 403  # no X-CSRF-Token


# ------------------------------------------------------------------ C2 upload


@pytest.mark.minio
@pytest.mark.parametrize("ext", ["pdf", "pptx", "docx", "txt"])
def test_upload_each_supported_type_creates_draft_pending(
    pg_minio_client, pg_session, queue_recorder, minio_cleanup, ext
):
    world = build_world(pg_session)
    headers = login(pg_minio_client, world.co)
    name, make, mime = UPLOADS[ext]
    resp = _upload(pg_minio_client, headers, world, name=name, data=make(), mime=mime)
    _track(pg_session, minio_cleanup)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert (body["status"], body["ingestion_status"], body["version_no"], body["ext"]) == (
        "DRAFT",
        "PENDING",
        1,
        ext,
    )
    assert queue_recorder.enqueued == [body["id"]]
    assert "storage_key" not in body  # object keys are internal


@pytest.mark.minio
def test_upload_legacy_doc_rejected_400(pg_minio_client, pg_session, minio_cleanup):
    world = build_world(pg_session)
    headers = login(pg_minio_client, world.co)
    resp = _upload(pg_minio_client, headers, world, name="old.doc", data=docs.make_legacy_ole())
    assert resp.status_code == 400 and "Legacy" in resp.json()["detail"]


@pytest.mark.minio
def test_upload_mime_mismatch_rejected(pg_minio_client, pg_session):
    world = build_world(pg_session)
    headers = login(pg_minio_client, world.co)
    resp = _upload(pg_minio_client, headers, world, name="fake.pdf", data=docs.make_txt("plain text"))
    assert resp.status_code == 400 and "does not match" in resp.json()["detail"]
    resp = _upload(
        pg_minio_client, headers, world, name="a.pdf", data=docs.make_text_pdf([["x"]]), mime="image/png"
    )
    assert resp.status_code == 400


@pytest.mark.minio
def test_oversize_upload_rejected_413_without_creating_rows(pg_minio_client, pg_session, monkeypatch):
    monkeypatch.setattr(settings, "upload_max_bytes", 1024)
    world = build_world(pg_session)
    headers = login(pg_minio_client, world.co)
    resp = _upload(pg_minio_client, headers, world, data=b"a" * 2048)
    assert resp.status_code == 413
    assert pg_session.scalar(select(func.count()).select_from(ContentVersion)) == 0


@pytest.mark.minio
def test_empty_file_rejected(pg_minio_client, pg_session):
    world = build_world(pg_session)
    headers = login(pg_minio_client, world.co)
    assert _upload(pg_minio_client, headers, world, data=b"").status_code == 400


@pytest.mark.minio
def test_unassigned_teacher_upload_rejected_404_no_data(pg_minio_client, pg_session):
    world = build_world(pg_session)
    headers = login(pg_minio_client, world.outsider)
    resp = _upload(pg_minio_client, headers, world)
    assert resp.status_code == 404
    assert pg_session.scalar(select(func.count()).select_from(ContentVersion)) == 0


@pytest.mark.minio
def test_upload_new_version_of_existing_asset_and_syllabus_conflict(
    pg_minio_client, pg_session, minio_cleanup
):
    world = build_world(pg_session)
    headers = login(pg_minio_client, world.co)
    first = _upload(pg_minio_client, headers, world, content_type="SYLLABUS", title="Syllabus")
    again = _upload(pg_minio_client, headers, world, content_type="SYLLABUS", title="Syllabus 2")
    assert (first.status_code, again.status_code) == (201, 409)
    v2 = _upload(
        pg_minio_client,
        headers,
        world,
        content_type="SYLLABUS",
        content_asset_id=first.json()["content_asset_id"],
    )
    _track(pg_session, minio_cleanup)
    assert v2.status_code == 201 and v2.json()["version_no"] == 2


@pytest.mark.minio
def test_upload_rate_limited_per_teacher(pg_minio_client, pg_session, monkeypatch, minio_cleanup):
    monkeypatch.setattr(settings, "rate_limit_upload_per_teacher_per_window", 1)
    world = build_world(pg_session)
    headers = login(pg_minio_client, world.co)
    assert _upload(pg_minio_client, headers, world).status_code == 201
    assert _upload(pg_minio_client, headers, world).status_code == 429
    _track(pg_session, minio_cleanup)


# ------------------------------------------------------------------ C3..C7 reads, retry


def test_c3_lists_assets_with_versions_and_status(pg_client, pg_session):
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    make_version(pg_session, asset=asset, actor=world.co, version_no=1)
    make_version(pg_session, asset=asset, actor=world.co, version_no=2, ingestion=IngestionStatus.FAILED)
    pg_session.commit()
    headers = login(pg_client, world.co)
    body = pg_client.get(f"/teacher/subjects/{world.subject.id}/content/assets", headers=headers).json()
    assert [v["version_no"] for v in body[0]["versions"]] == [2, 1]
    login(pg_client, world.outsider)
    assert pg_client.get(f"/teacher/subjects/{world.subject.id}/content/assets").status_code == 404


def test_get_version_returns_stage_runs(pg_client, pg_session):
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.PENDING
    )
    pg_session.commit()
    from datetime import UTC, datetime

    from app.models.content import IngestionStageRun, StageStatus

    for stage in ("VALIDATE", "EXTRACT"):
        pg_session.add(
            IngestionStageRun(
                content_version_id=version.id,
                stage=stage,
                attempt=1,
                status=StageStatus.SUCCEEDED,
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                detail={"k": 1},
            )
        )
    pg_session.commit()
    login(pg_client, world.co)
    body = pg_client.get(f"/teacher/content/versions/{version.id}").json()
    assert [(r["stage"], r["status"]) for r in body["stage_runs"]] == [
        ("VALIDATE", "SUCCEEDED"),
        ("EXTRACT", "SUCCEEDED"),
    ]
    assert body["chunk_count"] == 0 and body["content_type"] == "NOTES"


def test_retry_failed_ingestion_resumes_from_failed_stage(pg_client, pg_session, queue_recorder):
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(
        pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.FAILED
    )
    version.failed_stage, version.failure_message = "OCR", "OCR could not read page(s) 2"
    pg_session.commit()
    headers = login(pg_client, world.co)
    resp = pg_client.post(f"/teacher/content/versions/{version.id}/retry", headers=headers)
    assert resp.status_code == 200 and resp.json()["ingestion_status"] == "PENDING"
    assert queue_recorder.enqueued == [str(version.id)]
    assert (
        pg_client.post(f"/teacher/content/versions/{version.id}/retry", headers=headers).status_code == 200
    )  # still PENDING -> allowed
    login(pg_client, world.outsider)
    assert (
        pg_client.post(
            f"/teacher/content/versions/{version.id}/retry",
            headers={"X-CSRF-Token": pg_client.cookies.get("csrf_token")},
        ).status_code
        == 404
    )


def test_chunk_list_returns_metadata_but_never_vectors(pg_client, pg_session):
    world = build_world(pg_session)
    cfg = make_embedding_config(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    version = make_version(pg_session, asset=asset, actor=world.co, version_no=1)
    make_chunk(
        pg_session,
        version=version,
        subject_id=world.subject.id,
        config=cfg,
        index=0,
        text="Binary trees",
        unit_no=2,
        locator="page:9",
    )
    pg_session.commit()
    login(pg_client, world.co)
    body = pg_client.get(f"/teacher/content/versions/{version.id}/chunks?limit=10").json()
    assert body[0]["unit_no"] == 2 and body[0]["locator"] == "page:9" and body[0]["chunk_type"] == "NOTES"
    assert "embedding" not in body[0]
    assert (
        len(pg_client.get(f"/teacher/content/versions/{version.id}/chunks?limit=0").json()) == 1
    )  # limit clamped to >= 1


def test_chunk_ref_resolves_to_version_file_locator_after_supersede(pg_client, pg_session):
    from app.services import content_service

    world = build_world(pg_session)
    cfg = make_embedding_config(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    v1 = make_version(pg_session, asset=asset, actor=world.co, version_no=1)
    v2 = make_version(pg_session, asset=asset, actor=world.co, version_no=2)
    chunk = make_chunk(
        pg_session,
        version=v1,
        subject_id=world.subject.id,
        config=cfg,
        index=0,
        text="Binary trees",
        locator="page:4",
    )
    pg_session.commit()
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v2.id, reason=None)
    login(pg_client, world.co)
    body = pg_client.get(f"/teacher/content/chunks/{chunk.id}").json()
    assert (body["content_version_id"], body["version_no"], body["version_status"]) == (
        str(v1.id),
        1,
        "SUPERSEDED",
    )
    assert (body["source_file"], body["locator"]) == (v1.original_filename, "page:4")


def test_chunk_of_another_subject_is_404(pg_client, pg_session):
    world_a, world_b = build_world(pg_session, tag="a"), build_world(pg_session, tag="b")
    cfg = make_embedding_config(pg_session)
    asset = make_asset(pg_session, subject_id=world_b.subject.id, actor=world_b.co)
    v = make_version(pg_session, asset=asset, actor=world_b.co, version_no=1)
    chunk = make_chunk(pg_session, version=v, subject_id=world_b.subject.id, config=cfg, index=0, text="x")
    pg_session.commit()
    login(pg_client, world_a.co)
    assert pg_client.get(f"/teacher/content/chunks/{chunk.id}").status_code == 404
    assert pg_client.get(f"/teacher/content/versions/{v.id}/chunks").status_code == 404


# ------------------------------------------------------------------ C8 / C9 owner-only


def test_activate_endpoint_role_matrix(pg_client, pg_session):
    """AC-005: Owner activates; CO and unassigned Teachers are rejected."""
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    v1 = make_version(pg_session, asset=asset, actor=world.co, version_no=1)
    pg_session.commit()
    url = f"/teacher/content/versions/{v1.id}/activate"
    headers = login(pg_client, world.co)
    assert pg_client.post(url, headers=headers, json={"reason": "x"}).status_code == 403
    headers = login(pg_client, world.outsider)
    assert pg_client.post(url, headers=headers, json={}).status_code == 404
    headers = login(pg_client, world.owner)
    assert pg_client.post(url, json={}).status_code == 403  # CSRF header missing
    resp = pg_client.post(url, headers=headers, json={"reason": "approved"})
    assert resp.status_code == 200 and resp.json()["status"] == "ACTIVE"


def test_activate_failed_ingestion_returns_409(pg_client, pg_session):
    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    v = make_version(pg_session, asset=asset, actor=world.co, version_no=1, ingestion=IngestionStatus.FAILED)
    pg_session.commit()
    headers = login(pg_client, world.owner)
    assert (
        pg_client.post(f"/teacher/content/versions/{v.id}/activate", headers=headers, json={}).status_code
        == 409
    )


def test_rollback_endpoint_owner_only(pg_client, pg_session):
    from app.services import content_service

    world = build_world(pg_session)
    asset = make_asset(pg_session, subject_id=world.subject.id, actor=world.co)
    v1 = make_version(pg_session, asset=asset, actor=world.co, version_no=1)
    v2 = make_version(pg_session, asset=asset, actor=world.co, version_no=2)
    pg_session.commit()
    content_service.activate_version(pg_session, actor=world.owner, version_id=v1.id, reason=None)
    content_service.activate_version(pg_session, actor=world.owner, version_id=v2.id, reason=None)
    url = f"/teacher/content/assets/{asset.id}/rollback"
    body = {"target_version_id": str(v1.id), "reason": "regression"}
    assert pg_client.post(url, headers=login(pg_client, world.co), json=body).status_code == 403
    assert pg_client.post(url, headers=login(pg_client, world.outsider), json=body).status_code == 404
    resp = pg_client.post(url, headers=login(pg_client, world.owner), json=body)
    assert resp.status_code == 200 and resp.json()["id"] == str(v1.id) and resp.json()["status"] == "ACTIVE"


# ------------------------------------------------------------------ links C10..C13


def test_register_https_link_creates_draft_no_chunks(pg_client, pg_session):
    world = build_world(pg_session)
    headers = login(pg_client, world.co)
    url = f"/teacher/subjects/{world.subject.id}/content/links"
    resp = pg_client.post(
        url,
        headers=headers,
        json={
            "url": "https://example.com/x",
            "title": "T",
            "resource_type": "article",
            "topic_label": "Trees",
        },
    )
    assert resp.status_code == 201 and resp.json()["status"] == "DRAFT"
    assert pg_session.scalar(select(func.count()).select_from(ContentChunk)) == 0
    assert len(pg_client.get(url).json()) == 1


def test_register_http_link_rejected(pg_client, pg_session):
    world = build_world(pg_session)
    headers = login(pg_client, world.co)
    url = f"/teacher/subjects/{world.subject.id}/content/links"
    assert (
        pg_client.post(url, headers=headers, json={"url": "http://example.com", "title": "T"}).status_code
        == 400
    )
    assert (
        pg_client.post(url, headers=headers, json={"url": "javascript:alert(1)", "title": "T"}).status_code
        == 400
    )


def test_unassigned_teacher_link_rejected(pg_client, pg_session):
    world = build_world(pg_session)
    headers = login(pg_client, world.outsider)
    url = f"/teacher/subjects/{world.subject.id}/content/links"
    assert (
        pg_client.post(url, headers=headers, json={"url": "https://example.com", "title": "T"}).status_code
        == 404
    )
    assert pg_client.get(url).status_code == 404


def test_link_approve_and_revise_role_matrix(pg_client, pg_session):
    world = build_world(pg_session)
    url = f"/teacher/subjects/{world.subject.id}/content/links"
    payload = {"url": "https://example.com/a", "title": "A"}
    link = pg_client.post(url, headers=login(pg_client, world.co), json=payload).json()
    assert (
        pg_client.post(
            f"/teacher/content/links/{link['id']}/approve", headers=login(pg_client, world.co), json={}
        ).status_code
        == 403
    )
    assert (
        pg_client.post(
            f"/teacher/content/links/{link['id']}/approve", headers=login(pg_client, world.outsider), json={}
        ).status_code
        == 404
    )
    approved = pg_client.post(
        f"/teacher/content/links/{link['id']}/approve",
        headers=login(pg_client, world.owner),
        json={"reason": "ok"},
    )
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    revision = pg_client.post(
        f"/teacher/content/links/{link['id']}/revisions",
        headers=login(pg_client, world.co),
        json={"url": "https://example.com/b", "title": "B"},
    )
    assert (
        revision.status_code == 201
        and revision.json()["status"] == "DRAFT"
        and revision.json()["supersedes_link_id"] == link["id"]
    )


# ------------------------------------------------------------------ immutability: no mutating routes


@pytest.mark.parametrize(
    "method,path",
    [
        ("put", "/teacher/content/versions/{v}"),
        ("patch", "/teacher/content/versions/{v}"),
        ("delete", "/teacher/content/versions/{v}"),
        ("put", "/teacher/content/chunks/{c}"),
        ("patch", "/teacher/content/chunks/{c}"),
        ("delete", "/teacher/content/chunks/{c}"),
        ("put", "/teacher/content/links/{l}"),
        ("patch", "/teacher/content/links/{l}"),
        ("delete", "/teacher/content/links/{l}"),
    ],
)
def test_no_mutating_routes_for_versions_chunks_approved_links_405_404(pg_client, pg_session, method, path):
    import uuid

    world = build_world(pg_session)
    headers = login(pg_client, world.owner)
    url = path.format(v=uuid.uuid4(), c=uuid.uuid4(), l=uuid.uuid4())
    assert getattr(pg_client, method)(url, headers=headers).status_code in (404, 405)


def test_no_edit_route_exists_in_the_router_at_all():
    from app.api.routes import teacher_content

    unsafe = {m for r in teacher_content.router.routes for m in r.methods} & {"PUT", "PATCH", "DELETE"}
    assert unsafe == set()
