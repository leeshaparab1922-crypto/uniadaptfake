"""Recommendation-only HTTPS resource links. FR-CON-001 (register), FR-CON-004
(approve; approved links are never edited in place), BUS-047, NFR-SEC-009.

A link is stored as metadata only: nothing is fetched, no chunk or embedding is
ever created for it. A "revision" is a new DRAFT linked to the prior link
(`supersedes_link_id`); when the Owner approves it, the prior APPROVED link
becomes SUPERSEDED and stays resolvable.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.content import ApprovedResourceLink, LinkStatus
from app.models.subject import Unit
from app.models.user import User
from app.services import audit
from app.services.content_service import _assigned, _log_denied, require_assigned, require_owner
from app.services.ingestion import validators

RESOURCE_TYPES = ("ARTICLE", "VIDEO", "BOOK", "TUTORIAL", "OTHER")


def _check_fields(
    db: Session,
    *,
    subject_id: uuid.UUID,
    url: str | None,
    title: str | None,
    resource_type: str | None,
    est_minutes: int | None,
    unit_id: uuid.UUID | None,
    topic_label: str | None,
) -> dict:
    clean_url = validators.validate_https_url(url)
    clean_title = validators.validate_title(title)
    rtype = (resource_type or "OTHER").upper()
    if rtype not in RESOURCE_TYPES:
        raise ValidationError(f"Resource type must be one of: {', '.join(RESOURCE_TYPES)}.")
    if est_minutes is not None and est_minutes <= 0:
        raise ValidationError("Estimated minutes must be positive.")
    if unit_id is not None:
        unit = db.get(Unit, unit_id)
        if unit is None or unit.subject_id != subject_id:
            raise ValidationError("Unit does not belong to this Subject.")
    label = (topic_label or "").strip() or None
    if label and len(label) > 255:
        raise ValidationError("Topic label must be at most 255 characters.")
    return {
        "url": clean_url,
        "title": clean_title,
        "resource_type": rtype,
        "est_minutes": est_minutes,
        "unit_id": unit_id,
        "topic_label": label,
    }


def register_link(
    db: Session,
    *,
    actor: User,
    subject_id: uuid.UUID,
    url: str | None,
    title: str | None,
    resource_type: str | None,
    est_minutes: int | None = None,
    unit_id: uuid.UUID | None = None,
    topic_label: str | None = None,
) -> ApprovedResourceLink:
    require_assigned(db, actor, subject_id)
    fields = _check_fields(
        db,
        subject_id=subject_id,
        url=url,
        title=title,
        resource_type=resource_type,
        est_minutes=est_minutes,
        unit_id=unit_id,
        topic_label=topic_label,
    )
    link = ApprovedResourceLink(
        subject_id=subject_id, status=LinkStatus.DRAFT, uploaded_by=actor.id, **fields
    )
    db.add(link)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="REGISTER_RESOURCE_LINK",
        entity_type="approved_resource_link",
        entity_id=link.id,
        after={"subject_id": str(subject_id), "url": link.url, "status": "DRAFT"},
    )
    db.commit()
    return link


def list_links(db: Session, teacher: User, subject_id: uuid.UUID) -> list[ApprovedResourceLink]:
    require_assigned(db, teacher, subject_id)
    return list(
        db.scalars(
            select(ApprovedResourceLink)
            .where(ApprovedResourceLink.subject_id == subject_id)
            .order_by(ApprovedResourceLink.created_at.desc())
        )
    )


def _get_link(db: Session, teacher: User, link_id: uuid.UUID) -> ApprovedResourceLink:
    link = db.get(ApprovedResourceLink, link_id)
    if link is None or not _assigned(db, teacher.id, link.subject_id):
        _log_denied(teacher, "link_not_assigned_or_missing", link_id=link_id)
        raise NotFoundError("Link not found, or not assigned to this Teacher.")
    return link


def create_revision(
    db: Session,
    *,
    actor: User,
    link_id: uuid.UUID,
    url: str | None,
    title: str | None,
    resource_type: str | None,
    est_minutes: int | None = None,
    unit_id: uuid.UUID | None = None,
    topic_label: str | None = None,
) -> ApprovedResourceLink:
    prior = _get_link(db, actor, link_id)
    # Only the current APPROVED link is revised (finding m7): a DRAFT is not yet published, so
    # a correction is a new link, and a SUPERSEDED link is history.
    if prior.status != LinkStatus.APPROVED:
        raise ConflictError("Only an approved link can be revised. Add a new link instead.")
    fields = _check_fields(
        db,
        subject_id=prior.subject_id,
        url=url,
        title=title,
        resource_type=resource_type,
        est_minutes=est_minutes,
        unit_id=unit_id,
        topic_label=topic_label,
    )
    revision = ApprovedResourceLink(
        subject_id=prior.subject_id,
        status=LinkStatus.DRAFT,
        uploaded_by=actor.id,
        supersedes_link_id=prior.id,
        **fields,
    )
    db.add(revision)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="REVISE_RESOURCE_LINK",
        entity_type="approved_resource_link",
        entity_id=revision.id,
        before={"prior_link_id": str(prior.id), "prior_status": prior.status.value},
        after={"status": "DRAFT"},
    )
    db.commit()
    return revision


def approve_link(db: Session, *, actor: User, link_id: uuid.UUID, reason: str | None) -> ApprovedResourceLink:
    link = _get_link(db, actor, link_id)
    require_owner(db, actor, link.subject_id)
    # Lock the link and the link it revises so two approvals cannot race (finding m7).
    locked_ids = [link.id] + ([link.supersedes_link_id] if link.supersedes_link_id else [])
    db.execute(
        select(ApprovedResourceLink.id)
        .where(ApprovedResourceLink.id.in_(locked_ids))
        .order_by(ApprovedResourceLink.id)
        .with_for_update()
    )
    db.refresh(link)
    if link.status != LinkStatus.DRAFT:
        raise ConflictError("Only a DRAFT link can be approved.")
    superseded = None
    if link.supersedes_link_id is not None:
        prior = db.get(ApprovedResourceLink, link.supersedes_link_id)
        if prior is not None:
            db.refresh(prior)
        if prior is None or prior.status != LinkStatus.APPROVED:
            raise ConflictError(
                "The link this revision replaces is no longer the approved one. Revise the current link."
            )
        prior.status = LinkStatus.SUPERSEDED
        superseded = prior.id
    link.status = LinkStatus.APPROVED
    link.approved_by = actor.id
    link.approved_at = datetime.now(UTC)
    audit.record(
        db,
        actor=actor,
        action="APPROVE_RESOURCE_LINK",
        entity_type="approved_resource_link",
        entity_id=link.id,
        before={"status": "DRAFT"},
        after={"status": "APPROVED", "superseded": str(superseded) if superseded else None},
        reason=reason,
    )
    db.commit()
    return link
