"""Versioned duplicate-Topic similarity threshold (BUS-050, FR-CUR-002, ADR-0015).

A threshold row belongs to ONE embedding configuration. It starts DRAFT (configured default:
0.72 per ADR-0020; the SRS initial value was 0.92) and may become ACTIVE only after a recorded
validation (`validation_report`, status VALIDATED); a changed model or threshold is a NEW row,
never an edit of an old one. Curriculum approval requires the version's threshold to be ACTIVE
for the version's embedding configuration.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.curriculum import SimilarityThreshold, ThresholdStatus
from app.models.embedding_config import EmbeddingConfig
from app.models.user import User
from app.services import audit

THRESHOLD_NAME = "topic_duplicate"
NOT_VALIDATED_MESSAGE = (
    "The duplicate-detection threshold for the current embedding model has not been validated. "
    "An administrator must run the threshold validation before curriculum can be approved."
)


def _threshold_value(raw: str | float | Decimal) -> Decimal:
    value = Decimal(str(raw))
    if not Decimal(0) <= value <= Decimal(1):
        raise ValidationError("Threshold must be between 0 and 1.")
    return value.quantize(Decimal("0.001"))


def create_draft_threshold(
    db: Session, config: EmbeddingConfig, *, value: str | float | Decimal | None = None
) -> SimilarityThreshold:
    row = SimilarityThreshold(
        embedding_config_id=config.id,
        name=THRESHOLD_NAME,
        value=_threshold_value(value if value is not None else settings.duplicate_threshold_default),
        status=ThresholdStatus.DRAFT,
    )
    db.add(row)
    db.flush()
    audit.record(
        db,
        actor=None,
        action="CREATE_SIMILARITY_THRESHOLD",
        entity_type="similarity_threshold",
        entity_id=row.id,
        after={"value": str(row.value), "status": "DRAFT", "embedding_config_id": str(config.id)},
    )
    return row


def resolve_threshold(db: Session, config: EmbeddingConfig) -> SimilarityThreshold:
    """The ACTIVE threshold for this configuration, else the newest one (so the UI can show a
    'not validated' blocker), creating the initial DRAFT row (configured default) when none exists."""
    rows = list(
        db.scalars(
            select(SimilarityThreshold)
            .where(
                SimilarityThreshold.name == THRESHOLD_NAME,
                SimilarityThreshold.embedding_config_id == config.id,
                SimilarityThreshold.status != ThresholdStatus.RETIRED,
            )
            .order_by(SimilarityThreshold.created_at.desc(), SimilarityThreshold.id)
        )
    )
    for row in rows:
        if row.status == ThresholdStatus.ACTIVE:
            return row
    if rows:
        return rows[0]
    row = create_draft_threshold(db, config)
    db.commit()
    return row


def threshold_blocker(threshold: SimilarityThreshold | None, config_id: uuid.UUID | None) -> str | None:
    if (
        threshold is None
        or threshold.status != ThresholdStatus.ACTIVE
        or threshold.embedding_config_id != config_id
    ):
        return NOT_VALIDATED_MESSAGE
    return None


def record_validation(
    db: Session,
    threshold_id: uuid.UUID,
    *,
    report: dict,
    passed: bool,
    actor: User | None = None,
) -> SimilarityThreshold:
    """Store the validation report (P-7). Passing -> VALIDATED; failing keeps it DRAFT."""
    row = db.get(SimilarityThreshold, threshold_id)
    if row is None:
        raise NotFoundError("Threshold not found.")
    if row.status in (ThresholdStatus.ACTIVE, ThresholdStatus.RETIRED):
        raise ConflictError("An active or retired threshold cannot be re-validated; create a new version.")
    row.validation_report = report
    if passed:
        row.status = ThresholdStatus.VALIDATED
        row.validated_at = datetime.now(UTC)
        row.validated_by = actor.id if actor is not None else None
    else:
        row.status = ThresholdStatus.DRAFT
        row.validated_at = None
        row.validated_by = None
    audit.record(
        db,
        actor=actor,
        action="VALIDATE_SIMILARITY_THRESHOLD",
        entity_type="similarity_threshold",
        entity_id=row.id,
        after={"status": row.status.value, "passed": passed, "value": str(row.value)},
    )
    db.commit()
    return row


def activate_threshold(
    db: Session, threshold_id: uuid.UUID, *, actor: User | None = None
) -> SimilarityThreshold:
    """VALIDATED -> ACTIVE; the previous ACTIVE one for the same configuration is RETIRED."""
    row = db.get(SimilarityThreshold, threshold_id)
    if row is None:
        raise NotFoundError("Threshold not found.")
    if row.status != ThresholdStatus.VALIDATED:
        raise ConflictError("Only a VALIDATED threshold can be activated; run the validation first.")
    previous = db.scalar(
        select(SimilarityThreshold).where(
            SimilarityThreshold.name == row.name,
            SimilarityThreshold.embedding_config_id == row.embedding_config_id,
            SimilarityThreshold.status == ThresholdStatus.ACTIVE,
        )
    )
    if previous is not None:
        previous.status = ThresholdStatus.RETIRED
        db.flush()
    row.status = ThresholdStatus.ACTIVE
    audit.record(
        db,
        actor=actor,
        action="ACTIVATE_SIMILARITY_THRESHOLD",
        entity_type="similarity_threshold",
        entity_id=row.id,
        before={"previous_active": str(previous.id) if previous else None},
        after={"status": "ACTIVE", "value": str(row.value)},
    )
    db.commit()
    return row
