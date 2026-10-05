"""Teacher shared-content endpoints C1..C13. FR-CON-001..004.

Role gate is TEACHER; *assignment* and *Subject Owner* checks happen in the
service layer at query level (NFR-SEC-006/007). There are deliberately no
PUT/PATCH/DELETE routes for versions, chunks or approved links: approved
content is never edited in place (FR-CON-004, BUS-039).

Upload size (plan P-12): `app.core.body_limit.BodySizeLimitMiddleware` rejects any
request body over the limit (declared or actually received) with 413 before
routing, auth, or form parsing. The route then copies the file part into a temp
file with a hard per-file cap. A reverse proxy in front of the app should also
cap request bodies (see the .env.example note).
"""

from __future__ import annotations

import os
import tempfile
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.config import settings
from app.core.deps import (
    CurrentUser,
    DbSession,
    IngestionQueueDep,
    ObjectStoreDep,
    RateLimiterDep,
    csrf_protect,
    require_role,
)
from app.core.errors import PayloadTooLargeError, RateLimitedError
from app.models.content import ContentType
from app.models.user import UserRole
from app.schemas.content import (
    AssignedSubjectOut,
    ChunkOut,
    ChunkReferenceOut,
    ContentAssetOut,
    ContentVersionDetailOut,
    ContentVersionOut,
    DecisionRequest,
    RollbackRequest,
    StageRunOut,
    UnitBrief,
)
from app.schemas.resource_link import ResourceLinkCreate, ResourceLinkOut
from app.services import content_service, resource_link_service

router = APIRouter(
    prefix="/teacher",
    tags=["teacher-content"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.TEACHER))],
)


def _stream_to_tempfile(upload: UploadFile, max_bytes: int) -> str:
    fd, path = tempfile.mkstemp(prefix="upload_")
    total = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := upload.file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise PayloadTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.")
                out.write(chunk)
    except BaseException:
        os.unlink(path)
        raise
    return path


def _version_out(version) -> ContentVersionOut:
    out = ContentVersionOut.model_validate(version)
    window = content_service.retry_state(version)
    out.can_retry = window.can_retry
    out.retry_available_at = window.available_at
    return out


# C1
@router.get("/subjects", response_model=list[AssignedSubjectOut])
def list_my_subjects(db: DbSession, current_user: CurrentUser) -> list[AssignedSubjectOut]:
    return [
        AssignedSubjectOut(
            id=item.subject.id,
            code=item.subject.code,
            name=item.subject.name,
            semester_no=item.subject.semester_no,
            is_owner=item.is_owner,
            units=[UnitBrief.model_validate(u) for u in item.units],
        )
        for item in content_service.list_assigned_subjects(db, current_user)
    ]


# C2
@router.post(
    "/subjects/{subject_id}/content/uploads",
    response_model=ContentVersionOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_content(
    subject_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    store: ObjectStoreDep,
    queue: IngestionQueueDep,
    limiter: RateLimiterDep,
    file: Annotated[UploadFile, File()],
    content_type: Annotated[ContentType, Form()],
    title: Annotated[str | None, Form()] = None,
    unit_id: Annotated[uuid.UUID | None, Form()] = None,
    all_units: Annotated[bool, Form()] = False,
    content_asset_id: Annotated[uuid.UUID | None, Form()] = None,
) -> ContentVersionOut:
    if not limiter.hit(
        f"upload:{current_user.id}",
        limit=settings.rate_limit_upload_per_teacher_per_window,
        window_seconds=settings.rate_limit_window_seconds,
    ):
        raise RateLimitedError("Too many uploads. Please try again later.")

    path = _stream_to_tempfile(file, settings.upload_max_bytes)
    try:
        version = content_service.upload_content(
            db,
            actor=current_user,
            subject_id=subject_id,
            content_type=content_type,
            title=title,
            unit_id=unit_id,
            all_units=all_units,
            content_asset_id=content_asset_id,
            original_filename=file.filename,
            declared_content_type=file.content_type,
            local_path=path,
            store=store,
            queue=queue,
        )
    finally:
        os.unlink(path)
    return _version_out(version)


# C3
@router.get("/subjects/{subject_id}/content/assets", response_model=list[ContentAssetOut])
def list_assets(subject_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> list[ContentAssetOut]:
    return [
        ContentAssetOut(
            id=item.asset.id,
            subject_id=item.asset.subject_id,
            content_type=item.asset.content_type,
            title=item.asset.title,
            versions=[_version_out(v) for v in item.versions],
        )
        for item in content_service.list_assets(db, current_user, subject_id)
    ]


# C4
@router.get("/content/versions/{version_id}", response_model=ContentVersionDetailOut)
def get_version(version_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> ContentVersionDetailOut:
    version, asset, runs, chunk_count = content_service.get_version_detail(db, current_user, version_id)
    base = _version_out(version).model_dump()
    return ContentVersionDetailOut(
        **base,
        content_type=asset.content_type,
        asset_title=asset.title,
        subject_id=asset.subject_id,
        chunk_count=chunk_count,
        stage_runs=[StageRunOut.model_validate(r) for r in runs],
    )


# C5
@router.post("/content/versions/{version_id}/retry", response_model=ContentVersionOut)
def retry_ingestion(
    version_id: uuid.UUID, db: DbSession, current_user: CurrentUser, queue: IngestionQueueDep
) -> ContentVersionOut:
    return _version_out(
        content_service.retry_ingestion(db, actor=current_user, version_id=version_id, queue=queue)
    )


# C6
@router.get("/content/versions/{version_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    version_id: uuid.UUID, db: DbSession, current_user: CurrentUser, limit: int = 50, offset: int = 0
) -> list[ChunkOut]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    chunks = content_service.list_chunks(db, current_user, version_id, limit=limit, offset=offset)
    return [ChunkOut.model_validate(c) for c in chunks]


# C7
@router.get("/content/chunks/{chunk_id}", response_model=ChunkReferenceOut)
def resolve_chunk(chunk_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> ChunkReferenceOut:
    chunk, version, asset = content_service.resolve_chunk(db, current_user, chunk_id)
    return ChunkReferenceOut(
        chunk=ChunkOut.model_validate(chunk),
        content_version_id=version.id,
        version_no=version.version_no,
        version_status=version.status,
        content_asset_id=asset.id,
        source_file=chunk.source_file,
        locator=chunk.locator,
    )


# C8 (Owner only)
@router.post("/content/versions/{version_id}/activate", response_model=ContentVersionOut)
def activate_version(
    version_id: uuid.UUID, payload: DecisionRequest, db: DbSession, current_user: CurrentUser
) -> ContentVersionOut:
    return _version_out(
        content_service.activate_version(db, actor=current_user, version_id=version_id, reason=payload.reason)
    )


# C9 (Owner only)
@router.post("/content/assets/{asset_id}/rollback", response_model=ContentVersionOut)
def rollback_asset(
    asset_id: uuid.UUID, payload: RollbackRequest, db: DbSession, current_user: CurrentUser
) -> ContentVersionOut:
    return _version_out(
        content_service.rollback_asset(
            db,
            actor=current_user,
            asset_id=asset_id,
            target_version_id=payload.target_version_id,
            reason=payload.reason,
        )
    )


# C10
@router.post(
    "/subjects/{subject_id}/content/links",
    response_model=ResourceLinkOut,
    status_code=status.HTTP_201_CREATED,
)
def register_link(
    subject_id: uuid.UUID, payload: ResourceLinkCreate, db: DbSession, current_user: CurrentUser
) -> ResourceLinkOut:
    link = resource_link_service.register_link(
        db, actor=current_user, subject_id=subject_id, **payload.model_dump()
    )
    return ResourceLinkOut.model_validate(link)


# C11
@router.get("/subjects/{subject_id}/content/links", response_model=list[ResourceLinkOut])
def list_links(subject_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> list[ResourceLinkOut]:
    return [
        ResourceLinkOut.model_validate(x)
        for x in resource_link_service.list_links(db, current_user, subject_id)
    ]


# C12 (Owner only)
@router.post("/content/links/{link_id}/approve", response_model=ResourceLinkOut)
def approve_link(
    link_id: uuid.UUID, payload: DecisionRequest, db: DbSession, current_user: CurrentUser
) -> ResourceLinkOut:
    link = resource_link_service.approve_link(db, actor=current_user, link_id=link_id, reason=payload.reason)
    return ResourceLinkOut.model_validate(link)


# C13
@router.post(
    "/content/links/{link_id}/revisions",
    response_model=ResourceLinkOut,
    status_code=status.HTTP_201_CREATED,
)
def revise_link(
    link_id: uuid.UUID, payload: ResourceLinkCreate, db: DbSession, current_user: CurrentUser
) -> ResourceLinkOut:
    link = resource_link_service.create_revision(
        db, actor=current_user, link_id=link_id, **payload.model_dump()
    )
    return ResourceLinkOut.model_validate(link)
