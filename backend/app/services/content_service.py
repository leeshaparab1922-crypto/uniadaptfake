"""Shared Subject content: authorization, upload, activation, rollback, retry,
and traceable reads. FR-CON-001, FR-CON-003, FR-CON-004 (BUS-039, BUS-043).

Authorization (plan assumption A-1), always enforced at query level:
- "assigned Teacher for Subject S" = holds a TeacherAssignment on any
  SubjectInstance of S. Not assigned -> NotFoundError (non-enumerating 404).
- "Subject Owner" = SubjectOwnerAssignment.owner_teacher_id (ADR-0003). An
  assigned non-Owner gets ForbiddenError (403) on owner-only actions.

ADR-0011: every mutation writes an audit_logs row in the same transaction.
Upload order is object-first: the original is written to MinIO (write-once key
with a fresh version UUID) before the database row, so a DB failure can leave
only an unreferenced object, never a row pointing at nothing.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.integrations.object_store import build_storage_key
from app.models.content import (
    ContentAsset,
    ContentChunk,
    ContentType,
    ContentVersion,
    ContentVersionStatus,
    IngestionStageRun,
    IngestionStatus,
)
from app.models.subject import Subject, Unit
from app.models.subject_instance import SubjectInstance, SubjectOwnerAssignment, TeacherAssignment
from app.models.user import User
from app.services import audit
from app.services.ingestion import mime as mime_check
from app.services.ingestion import validators
from app.services.ingestion.ports import IngestionQueue, ObjectStore
from app.services.ingestion_retry import RetryWindow, retry_window

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "Subject not found, or not assigned to this Teacher."
OWNER_ONLY_MESSAGE = "Only the Subject Owner can perform this action."


@dataclass(frozen=True)
class AssignedSubject:
    subject: Subject
    is_owner: bool
    units: list[Unit]


# ---------------------------------------------------------------- authorization


def _assigned(db: Session, teacher_id: uuid.UUID, subject_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(TeacherAssignment.id)
            .join(SubjectInstance, SubjectInstance.id == TeacherAssignment.subject_instance_id)
            .where(TeacherAssignment.teacher_id == teacher_id, SubjectInstance.subject_id == subject_id)
            .limit(1)
        )
        is not None
    )


def is_owner(db: Session, teacher_id: uuid.UUID, subject_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(SubjectOwnerAssignment.id).where(
                SubjectOwnerAssignment.subject_id == subject_id,
                SubjectOwnerAssignment.owner_teacher_id == teacher_id,
            )
        )
        is not None
    )


def _log_denied(teacher: User, reason: str, **ids: uuid.UUID | None) -> None:
    """Section 37 unauthorized access: return 403/404, reveal nothing, log the event.
    Logged with ids only, never names or emails (NFR-SEC-011)."""
    refs = " ".join(f"{k}={v}" for k, v in ids.items())
    logger.warning("content access denied: reason=%s teacher_id=%s %s", reason, teacher.id, refs)


def require_assigned(db: Session, teacher: User, subject_id: uuid.UUID) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None or not _assigned(db, teacher.id, subject_id):
        _log_denied(teacher, "not_assigned_or_missing", subject_id=subject_id)
        raise NotFoundError(NOT_FOUND_MESSAGE)
    return subject


def require_owner(db: Session, teacher: User, subject_id: uuid.UUID) -> Subject:
    subject = require_assigned(db, teacher, subject_id)
    if not is_owner(db, teacher.id, subject_id):
        _log_denied(teacher, "not_subject_owner", subject_id=subject_id)
        raise ForbiddenError(OWNER_ONLY_MESSAGE)
    return subject


def list_assigned_subjects(db: Session, teacher: User) -> list[AssignedSubject]:
    subjects = db.scalars(
        select(Subject)
        .join(SubjectInstance, SubjectInstance.subject_id == Subject.id)
        .join(TeacherAssignment, TeacherAssignment.subject_instance_id == SubjectInstance.id)
        .where(TeacherAssignment.teacher_id == teacher.id)
        .distinct()
        .order_by(Subject.code)
    ).all()
    result = []
    for subject in subjects:
        units = list(db.scalars(select(Unit).where(Unit.subject_id == subject.id).order_by(Unit.order_index)))
        result.append(AssignedSubject(subject, is_owner(db, teacher.id, subject.id), units))
    return result


def _version_with_asset(
    db: Session, teacher: User, version_id: uuid.UUID
) -> tuple[ContentVersion, ContentAsset]:
    version = db.get(ContentVersion, version_id)
    asset = db.get(ContentAsset, version.content_asset_id) if version is not None else None
    if version is None or asset is None or not _assigned(db, teacher.id, asset.subject_id):
        _log_denied(teacher, "version_not_assigned_or_missing", version_id=version_id)
        raise NotFoundError("Content version not found, or not assigned to this Teacher.")
    return version, asset


# ---------------------------------------------------------------- upload (FR-CON-001)


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def _check_unit_choice(content_type: ContentType, unit_id: uuid.UUID | None, all_units: bool) -> None:
    """Human decision 2026-10-04 (plan P-6 / finding m2): every non-syllabus upload names one
    Unit or explicitly "All units"; a syllabus always covers all Units. With "All units" (or a
    syllabus) the Unit comes from 'Unit N' headings, and ingestion fails if none match."""
    if content_type == ContentType.SYLLABUS and unit_id is not None:
        raise ValidationError("A syllabus covers all Units; do not choose a single Unit for it.")
    if unit_id is not None and all_units:
        raise ValidationError("Choose either one Unit or 'All units', not both.")
    if content_type != ContentType.SYLLABUS and unit_id is None and not all_units:
        raise ValidationError("Choose the Unit this file covers, or 'All units'.")


def upload_content(
    db: Session,
    *,
    actor: User,
    subject_id: uuid.UUID,
    content_type: ContentType,
    title: str | None,
    unit_id: uuid.UUID | None,
    content_asset_id: uuid.UUID | None,
    original_filename: str | None,
    all_units: bool = False,
    declared_content_type: str | None,
    local_path: str,
    store: ObjectStore,
    queue: IngestionQueue,
    max_bytes: int | None = None,
) -> ContentVersion:
    """Validate, store the original (write-once), register a DRAFT version and queue ingestion.

    Active/approved content is never touched (FR-CON-001 Post, BUS-039)."""
    require_assigned(db, actor, subject_id)
    _check_unit_choice(content_type, unit_id, all_units)

    ext = validators.validate_extension(original_filename)
    size = os.path.getsize(local_path)
    validators.validate_size(size, max_bytes or settings.upload_max_bytes)
    mime_type = mime_check.check_declared_vs_actual(local_path, ext, declared_content_type)
    if ext in ("pptx", "docx"):
        mime_check.check_archive_limits(
            local_path,
            max_uncompressed_bytes=settings.ingest_archive_max_uncompressed_bytes,
            max_compression_ratio=settings.ingest_archive_max_compression_ratio,
            max_members=settings.ingest_archive_max_members,
        )
    display_name = validators.safe_display_filename(original_filename)
    sha256 = _file_sha256(local_path)

    # Serialise version numbering / syllabus-asset creation per Subject.
    db.execute(select(Subject.id).where(Subject.id == subject_id).with_for_update())

    if unit_id is not None:
        unit = db.get(Unit, unit_id)
        if unit is None or unit.subject_id != subject_id:
            raise ValidationError("Unit does not belong to this Subject.")

    if content_asset_id is not None:
        asset = db.get(ContentAsset, content_asset_id)
        if asset is None or asset.subject_id != subject_id:
            raise NotFoundError("Content asset not found for this Subject.")
        if asset.content_type != content_type:
            raise ValidationError("Content type must match the existing asset when uploading a new version.")
    else:
        if content_type == ContentType.SYLLABUS and db.scalar(
            select(ContentAsset.id).where(
                ContentAsset.subject_id == subject_id, ContentAsset.content_type == ContentType.SYLLABUS
            )
        ):
            raise ConflictError(
                "This Subject already has a syllabus. Upload a new version of the existing syllabus."
            )
        asset = ContentAsset(
            subject_id=subject_id,
            content_type=content_type,
            title=validators.validate_title(title, what="Title"),
            created_by=actor.id,
        )
        db.add(asset)
        db.flush()

    version_no = (
        db.scalar(
            select(func.max(ContentVersion.version_no)).where(ContentVersion.content_asset_id == asset.id)
        )
        or 0
    ) + 1
    version_id = uuid.uuid4()
    key = build_storage_key(subject_id, asset.id, version_id, ext)

    with open(local_path, "rb") as fh:
        store.put_if_absent(key, fh, size, mime_type)

    version = ContentVersion(
        id=version_id,
        content_asset_id=asset.id,
        version_no=version_no,
        status=ContentVersionStatus.DRAFT,
        ingestion_status=IngestionStatus.PENDING,
        unit_id=unit_id,
        storage_key=key,
        original_filename=display_name,
        ext=ext,
        mime_type=mime_type,
        size_bytes=size,
        sha256=sha256,
        uploaded_by=actor.id,
    )
    db.add(version)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="UPLOAD_CONTENT_VERSION",
        entity_type="content_version",
        entity_id=version.id,
        after={
            "subject_id": str(subject_id),
            "content_asset_id": str(asset.id),
            "version_no": version_no,
            "content_type": content_type.value,
            "storage_key": key,
            "sha256": sha256,
            "size_bytes": size,
        },
    )
    db.commit()
    _enqueue_safely(queue, version.id)
    return version


def _enqueue_safely(queue: IngestionQueue, version_id: uuid.UUID) -> None:
    try:
        queue.enqueue(str(version_id))
    except Exception:  # noqa: BLE001 - the version stays PENDING and can be retried (C5)
        logger.exception("Could not queue ingestion for version %s; it remains PENDING.", version_id)


# ---------------------------------------------------------------- reads


@dataclass(frozen=True)
class AssetWithVersions:
    asset: ContentAsset
    versions: list[ContentVersion]


def list_assets(db: Session, teacher: User, subject_id: uuid.UUID) -> list[AssetWithVersions]:
    require_assigned(db, teacher, subject_id)
    assets = db.scalars(
        select(ContentAsset).where(ContentAsset.subject_id == subject_id).order_by(ContentAsset.created_at)
    ).all()
    result = []
    for asset in assets:
        versions = list(
            db.scalars(
                select(ContentVersion)
                .where(ContentVersion.content_asset_id == asset.id)
                .order_by(ContentVersion.version_no.desc())
            )
        )
        result.append(AssetWithVersions(asset, versions))
    return result


def get_version_detail(
    db: Session, teacher: User, version_id: uuid.UUID
) -> tuple[ContentVersion, ContentAsset, list[IngestionStageRun], int]:
    version, asset = _version_with_asset(db, teacher, version_id)
    runs = list(
        db.scalars(
            select(IngestionStageRun)
            .where(IngestionStageRun.content_version_id == version.id)
            .order_by(IngestionStageRun.attempt, IngestionStageRun.started_at)
        )
    )
    chunk_count = db.scalar(
        select(func.count()).select_from(ContentChunk).where(ContentChunk.content_version_id == version.id)
    )
    return version, asset, runs, int(chunk_count or 0)


def list_chunks(
    db: Session, teacher: User, version_id: uuid.UUID, *, limit: int, offset: int
) -> list[ContentChunk]:
    version, _ = _version_with_asset(db, teacher, version_id)
    return list(
        db.scalars(
            select(ContentChunk)
            .where(ContentChunk.content_version_id == version.id)
            .order_by(ContentChunk.chunk_index)
            .limit(limit)
            .offset(offset)
        )
    )


def resolve_chunk(
    db: Session, teacher: User, chunk_id: uuid.UUID
) -> tuple[ContentChunk, ContentVersion, ContentAsset]:
    """Resolve an immutable chunk reference to its version/file/locator. Works for any
    version status, so citations stay resolvable after supersession/rollback (NFR-DAT-002)."""
    chunk = db.get(ContentChunk, chunk_id)
    if chunk is None:
        _log_denied(teacher, "chunk_missing", chunk_id=chunk_id)
        raise NotFoundError("Chunk not found, or not assigned to this Teacher.")
    version, asset = _version_with_asset(db, teacher, chunk.content_version_id)
    return chunk, version, asset


# ---------------------------------------------------------------- retry (BUS-040)


def retry_state(version: ContentVersion, now: datetime | None = None) -> RetryWindow:
    """Whether this version may be retried now, and when a RUNNING one becomes retryable (M2)."""
    return retry_window(
        version_status=version.status.value,
        ingestion_status=version.ingestion_status.value,
        heartbeat_at=version.ingestion_heartbeat_at,
        now=now or datetime.now(UTC),
        stale_after_seconds=settings.effective_ingest_stale_after_seconds,
    )


def retry_ingestion(
    db: Session, *, actor: User, version_id: uuid.UUID, queue: IngestionQueue
) -> ContentVersion:
    """Any assigned Teacher may retry a FAILED or PENDING version at once, and a RUNNING
    version once it has had no activity for longer than the stale timeout (finding M2)."""
    _version_with_asset(db, actor, version_id)
    # Lock the row so two concurrent retries cannot both re-queue it (finding m1).
    version = db.execute(
        select(ContentVersion)
        .where(ContentVersion.id == version_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()
    if version.status != ContentVersionStatus.DRAFT:
        raise ConflictError("Only DRAFT versions can be re-ingested.")
    if version.ingestion_status == IngestionStatus.SUCCEEDED:
        raise ConflictError("Ingestion already succeeded for this version.")
    window = retry_state(version)
    if not window.can_retry:
        until = window.available_at.isoformat() if window.available_at else "later"
        raise ConflictError(
            f"Ingestion is still running for this version. If it stays stuck, retry after {until}."
        )
    before = {
        "ingestion_status": version.ingestion_status.value,
        "failed_stage": version.failed_stage,
        "ingestion_heartbeat_at": (
            version.ingestion_heartbeat_at.isoformat() if version.ingestion_heartbeat_at else None
        ),
    }
    version.ingestion_status = IngestionStatus.PENDING
    version.ingestion_heartbeat_at = None
    audit.record(
        db,
        actor=actor,
        action="RETRY_CONTENT_INGESTION",
        entity_type="content_version",
        entity_id=version.id,
        before=before,
        after={"ingestion_status": IngestionStatus.PENDING.value},
    )
    db.commit()
    _enqueue_safely(queue, version.id)
    return version


# ---------------------------------------------------------------- activate / rollback (FR-CON-004)


def _lock_asset(db: Session, asset_id: uuid.UUID) -> ContentAsset:
    return db.execute(select(ContentAsset).where(ContentAsset.id == asset_id).with_for_update()).scalar_one()


def activate_version(
    db: Session, *, actor: User, version_id: uuid.UUID, reason: str | None
) -> ContentVersion:
    """DRAFT (ingestion SUCCEEDED) -> ACTIVE; the prior ACTIVE becomes SUPERSEDED but stays
    intact and resolvable. Owner-only. Constitutes approval for Tutor/Recommendation use."""
    version, asset = _version_with_asset(db, actor, version_id)
    require_owner(db, actor, asset.subject_id)
    _lock_asset(db, asset.id)
    db.refresh(version)
    if version.status != ContentVersionStatus.DRAFT:
        raise ConflictError("Only a DRAFT version can be activated.")
    if version.ingestion_status != IngestionStatus.SUCCEEDED:
        raise ConflictError("Ingestion must have succeeded before this version can be activated.")

    previous = db.scalar(
        select(ContentVersion).where(
            ContentVersion.content_asset_id == asset.id, ContentVersion.status == ContentVersionStatus.ACTIVE
        )
    )
    if previous is not None:
        previous.status = ContentVersionStatus.SUPERSEDED
        db.flush()  # free the one-active-per-asset slot before activating
        version.supersedes_version_id = previous.id
    version.status = ContentVersionStatus.ACTIVE
    version.activated_by = actor.id
    version.activated_at = datetime.now(UTC)
    audit.record(
        db,
        actor=actor,
        action="ACTIVATE_CONTENT_VERSION",
        entity_type="content_version",
        entity_id=version.id,
        before={"previous_active": str(previous.id) if previous else None, "status": "DRAFT"},
        after={"status": "ACTIVE", "superseded": str(previous.id) if previous else None},
        reason=reason,
    )
    db.commit()
    return version


def rollback_asset(
    db: Session, *, actor: User, asset_id: uuid.UUID, target_version_id: uuid.UUID, reason: str | None
) -> ContentVersion:
    """Reactivate a valid prior (SUPERSEDED, successfully ingested) version. Pointer-only:
    no object or chunk is copied or moved (ADR-0018)."""
    asset = db.get(ContentAsset, asset_id)
    if asset is None or not _assigned(db, actor.id, asset.subject_id):
        _log_denied(actor, "asset_not_assigned_or_missing", asset_id=asset_id)
        raise NotFoundError("Content asset not found, or not assigned to this Teacher.")
    require_owner(db, actor, asset.subject_id)
    _lock_asset(db, asset.id)
    target = db.get(ContentVersion, target_version_id)
    if target is None or target.content_asset_id != asset.id:
        raise NotFoundError("Target version not found for this asset.")
    db.refresh(target)
    if (
        target.status != ContentVersionStatus.SUPERSEDED
        or target.ingestion_status != IngestionStatus.SUCCEEDED
    ):
        raise ConflictError("Rollback target must be a previously active, successfully ingested version.")

    current = db.scalar(
        select(ContentVersion).where(
            ContentVersion.content_asset_id == asset.id, ContentVersion.status == ContentVersionStatus.ACTIVE
        )
    )
    if current is not None:
        current.status = ContentVersionStatus.SUPERSEDED
        db.flush()
    target.status = ContentVersionStatus.ACTIVE
    target.activated_by = actor.id
    target.activated_at = datetime.now(UTC)
    audit.record(
        db,
        actor=actor,
        action="ROLLBACK_CONTENT_VERSION",
        entity_type="content_version",
        entity_id=target.id,
        before={"active": str(current.id) if current else None},
        after={"active": str(target.id)},
        reason=reason,
    )
    db.commit()
    return target
