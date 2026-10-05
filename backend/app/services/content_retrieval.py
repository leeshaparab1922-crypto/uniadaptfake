"""Scope-filtered chunk retrieval (FR-CON-002 Post: "Chunks are retrievable only
under correct subject/version/approval scope"). Used by later phases (Tutor,
Assessment); no HTTP endpoint exists for it in Phase 2.

Approved scope = ACTIVE version, ingestion SUCCEEDED, chunk embedded with the
*same* embedding configuration as the query vector. DRAFT/SUPERSEDED/failed
chunks are never similarity-searchable. Resolution by id/version (for citations)
is separate and works for any status.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import ContentChunk, ContentVersion, ContentVersionStatus, IngestionStatus


def retrieve_approved_chunks(
    db: Session,
    *,
    subject_id: uuid.UUID,
    query_embedding: Sequence[float],
    embedding_config_id: uuid.UUID,
    limit: int = 5,
    unit_no: int | None = None,
) -> list[tuple[ContentChunk, float]]:
    """Nearest chunks by cosine distance within the approved scope. Returns (chunk, distance)."""
    distance = ContentChunk.embedding.cosine_distance(list(query_embedding))
    stmt = (
        select(ContentChunk, distance.label("distance"))
        .join(ContentVersion, ContentVersion.id == ContentChunk.content_version_id)
        .where(
            ContentChunk.subject_id == subject_id,
            ContentChunk.embedding_config_id == embedding_config_id,
            ContentChunk.embedding.is_not(None),
            ContentVersion.status == ContentVersionStatus.ACTIVE,
            ContentVersion.ingestion_status == IngestionStatus.SUCCEEDED,
        )
        .order_by(distance)
        .limit(limit)
    )
    if unit_no is not None:
        stmt = stmt.where(ContentChunk.unit_no == unit_no)
    return [(row[0], float(row[1])) for row in db.execute(stmt).all()]


def chunks_for_version(
    db: Session, *, subject_id: uuid.UUID, content_version_id: uuid.UUID
) -> list[ContentChunk]:
    """All chunks of one specific version (used to feed curriculum extraction in slice 2B)."""
    return list(
        db.scalars(
            select(ContentChunk)
            .where(
                ContentChunk.subject_id == subject_id, ContentChunk.content_version_id == content_version_id
            )
            .order_by(ContentChunk.chunk_index)
        )
    )
