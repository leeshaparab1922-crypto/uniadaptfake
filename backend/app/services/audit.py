"""Shared audit-trail helper. ADR-0011: every service function that creates,
updates, deactivates, or deletes data on an Admin's (or other privileged
actor's) behalf writes an `audit_logs` row in the *same* transaction as the
mutation it records - no hand-built `AuditLog(...)` construction anywhere
else in the service layer.

Callers `db.add()` (via this helper) but do not `db.commit()` here - the
caller's own `db.commit()` covers both the business-data write and this
audit row atomically.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def record(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before=before,
        after=after,
        reason=reason,
        created_at=datetime.now(UTC),
    )
    db.add(entry)
    return entry
