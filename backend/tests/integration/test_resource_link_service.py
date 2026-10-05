"""FR-CON-001 (register link) / FR-CON-004 (approve, never edit in place), BUS-047, NFR-SEC-009.
Marker: pg."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.audit_log import AuditLog
from app.models.content import ApprovedResourceLink, ContentChunk, LinkStatus
from app.services import resource_link_service as links
from tests.support.world import build_world

pytestmark = pytest.mark.pg

GOOD = dict(url="https://example.com/trees", title="Trees explained", resource_type="video", est_minutes=20)


def test_register_https_link_creates_draft(pg_session):
    world = build_world(pg_session)
    link = links.register_link(
        pg_session, actor=world.co, subject_id=world.subject.id, topic_label="BST", **GOOD
    )
    assert (link.status, link.url, link.resource_type, link.topic_label) == (
        LinkStatus.DRAFT,
        "https://example.com/trees",
        "VIDEO",
        "BST",
    )
    assert link.uploaded_by == world.co.id and link.approved_by is None
    assert pg_session.scalar(select(AuditLog.action).where(AuditLog.action == "REGISTER_RESOURCE_LINK"))


def test_link_registration_makes_no_network_call_and_no_chunk_rows(pg_session, monkeypatch):
    import socket

    def boom(*a, **k):
        raise AssertionError("network access attempted: links must never be crawled")

    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket.socket, "connect", boom)
    world = build_world(pg_session)
    links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD)
    assert pg_session.scalar(select(func.count()).select_from(ContentChunk)) == 0


def test_link_never_creates_chunk_rows_even_after_approval(pg_session):
    world = build_world(pg_session)
    link = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD)
    links.approve_link(pg_session, actor=world.owner, link_id=link.id, reason=None)
    assert pg_session.scalar(select(func.count()).select_from(ContentChunk)) == 0


@pytest.mark.parametrize("url", ["http://example.com", "javascript:x", "file:///etc/passwd", "https://", ""])
def test_non_https_links_rejected(pg_session, url):
    world = build_world(pg_session)
    with pytest.raises(ValidationError):
        links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **{**GOOD, "url": url})


def test_db_check_rejects_non_https_even_if_service_bypassed(pg_session):
    world = build_world(pg_session)
    row = ApprovedResourceLink(
        subject_id=world.subject.id,
        url="http://x.com",
        title="t",
        resource_type="OTHER",
        status=LinkStatus.DRAFT,
        uploaded_by=world.co.id,
    )
    pg_session.add(row)
    with pytest.raises(IntegrityError):
        pg_session.flush()
    pg_session.rollback()


def test_invalid_metadata_rejected(pg_session):
    world = build_world(pg_session)
    for bad in ({"title": " "}, {"resource_type": "PODCASTS"}, {"est_minutes": 0}):
        with pytest.raises(ValidationError):
            links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **{**GOOD, **bad})


def test_unassigned_teacher_cannot_register_or_list(pg_session):
    world = build_world(pg_session)
    with pytest.raises(NotFoundError):
        links.register_link(pg_session, actor=world.outsider, subject_id=world.subject.id, **GOOD)
    with pytest.raises(NotFoundError):
        links.list_links(pg_session, world.outsider, world.subject.id)


def test_owner_approves_link(pg_session):
    world = build_world(pg_session)
    link = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD)
    approved = links.approve_link(pg_session, actor=world.owner, link_id=link.id, reason="vetted")
    assert (
        approved.status == LinkStatus.APPROVED
        and approved.approved_by == world.owner.id
        and approved.approved_at
    )
    entry = pg_session.scalar(select(AuditLog).where(AuditLog.action == "APPROVE_RESOURCE_LINK"))
    assert entry.reason == "vetted" and entry.actor_id == world.owner.id


def test_co_cannot_approve_link(pg_session):
    world = build_world(pg_session)
    link = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD)
    with pytest.raises(ForbiddenError):
        links.approve_link(pg_session, actor=world.co, link_id=link.id, reason=None)
    with pytest.raises(NotFoundError):
        links.approve_link(pg_session, actor=world.outsider, link_id=link.id, reason=None)
    assert link.status == LinkStatus.DRAFT


def test_only_draft_can_be_approved(pg_session):
    world = build_world(pg_session)
    link = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD)
    links.approve_link(pg_session, actor=world.owner, link_id=link.id, reason=None)
    with pytest.raises(ConflictError):
        links.approve_link(pg_session, actor=world.owner, link_id=link.id, reason=None)


def test_revision_creates_new_draft_linked_to_prior_approved_untouched(pg_session):
    world = build_world(pg_session)
    first = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD)
    links.approve_link(pg_session, actor=world.owner, link_id=first.id, reason=None)
    revision = links.create_revision(
        pg_session, actor=world.co, link_id=first.id, **{**GOOD, "title": "Better title"}
    )
    assert (revision.status, revision.supersedes_link_id, revision.title) == (
        LinkStatus.DRAFT,
        first.id,
        "Better title",
    )
    assert (first.status, first.title) == (LinkStatus.APPROVED, "Trees explained")  # never edited in place


def test_approving_a_revision_supersedes_the_prior_link(pg_session):
    world = build_world(pg_session)
    first = links.register_link(pg_session, actor=world.co, subject_id=world.subject.id, **GOOD)
    links.approve_link(pg_session, actor=world.owner, link_id=first.id, reason=None)
    revision = links.create_revision(pg_session, actor=world.co, link_id=first.id, **GOOD)
    links.approve_link(pg_session, actor=world.owner, link_id=revision.id, reason=None)
    pg_session.refresh(first)
    assert (first.status, revision.status) == (LinkStatus.SUPERSEDED, LinkStatus.APPROVED)
    with pytest.raises(ConflictError):
        links.create_revision(pg_session, actor=world.co, link_id=first.id, **GOOD)


def test_unit_must_belong_to_subject(pg_session):
    import uuid

    world = build_world(pg_session)
    with pytest.raises(ValidationError):
        links.register_link(
            pg_session, actor=world.co, subject_id=world.subject.id, unit_id=uuid.uuid4(), **GOOD
        )
    ok = links.register_link(
        pg_session, actor=world.co, subject_id=world.subject.id, unit_id=world.units[0].id, **GOOD
    )
    assert ok.unit_id == world.units[0].id
