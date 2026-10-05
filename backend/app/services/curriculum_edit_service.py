"""Teacher graph editing: rename, merge, split, reorder, classify, hours, add/delete edges,
delete Topic. FR-CUR-003 (BUS-043, plan A-4/A-5/A-6).

Any assigned Teacher (PRIMARY or CO) may edit a DRAFT (or RETURNED) curriculum; an ACTIVE or
SUPERSEDED version is immutable (409). Every edit, in ONE transaction: mutates the working copy,
bumps `revision`, writes an audit row, re-runs the deterministic validation, and leaves approval
pending (the Owner still has to approve; a stale validation blocks approval). Stable Topic ids
are preserved on rename; merge/split record lineage in `topic_mappings`.

Deterministic and LLM-free, like `curriculum_service`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.curriculum import (
    BloomLevel,
    CurriculumStatus,
    CurriculumVersion,
    EdgeSource,
    MappingKind,
    Topic,
    TopicClassification,
    TopicMapping,
    TopicPrereq,
    TopicSourceChunk,
    TopicVersion,
    ValidationStatus,
)
from app.models.subject import Subject, Unit
from app.models.user import User
from app.services import audit
from app.services import curriculum_service as cs
from app.services import similarity_config_service as thresholds
from app.services.embedding_config_service import get_or_create_active_config
from app.services.ingestion.ports import Embedder

EDIT_STATE_MESSAGE = "Only a DRAFT curriculum can be edited; an approved version is immutable."
MAX_NAME = 255


@dataclass
class SplitPart:
    name: str
    outcomes: list[str] | None = None
    est_hours: float | None = None
    prereq_topic_ids: list[uuid.UUID] = field(default_factory=list)
    dependent_topic_ids: list[uuid.UUID] = field(default_factory=list)


# ------------------------------------------------------------------ plumbing


def _open_for_edit(db: Session, actor: User, curriculum_version_id: uuid.UUID) -> CurriculumVersion:
    cv = cs.version_for_teacher(db, actor, curriculum_version_id)
    # Resolve (and if needed create) the embedding config / threshold rows BEFORE any mutation,
    # because creating them commits and must not commit a half-done edit.
    thresholds.resolve_threshold(db, get_or_create_active_config(db))
    cv = cs.lock_version(db, cv.id)
    if cv.status not in cs.EDITABLE_STATUSES:
        raise ConflictError(EDIT_STATE_MESSAGE)
    return cv


def _finish(
    db: Session,
    cv: CurriculumVersion,
    *,
    actor: User,
    embedder: Embedder,
    action: str,
    before: dict | None,
    after: dict | None,
) -> CurriculumVersion:
    _resequence(db, cv.id)
    if cv.status == CurriculumStatus.RETURNED:
        cv.status = CurriculumStatus.DRAFT
    cv.revision += 1
    cv.validation_status = ValidationStatus.NOT_RUN
    audit.record(
        db,
        actor=actor,
        action=action,
        entity_type="curriculum_version",
        entity_id=cv.id,
        before=before,
        after={**(after or {}), "revision": cv.revision},
    )
    db.flush()
    cs.validate_version(db, cv.id, embedder=embedder, actor=actor, commit=False)
    db.commit()
    return cv


def _resequence(db: Session, cv_id: uuid.UUID) -> None:
    rows = list(
        db.scalars(
            select(TopicVersion)
            .where(TopicVersion.curriculum_version_id == cv_id)
            .order_by(TopicVersion.unit_id, TopicVersion.order_index, TopicVersion.id)
        )
    )
    counters: dict[uuid.UUID | None, int] = {}
    for tv in rows:
        counters[tv.unit_id] = counters.get(tv.unit_id, 0) + 1
        if tv.order_index != counters[tv.unit_id]:
            tv.order_index = counters[tv.unit_id]
    db.flush()


def _tv(db: Session, cv: CurriculumVersion, topic_id: uuid.UUID) -> TopicVersion:
    tv = db.scalar(
        select(TopicVersion).where(
            TopicVersion.curriculum_version_id == cv.id, TopicVersion.topic_id == topic_id
        )
    )
    if tv is None:
        raise NotFoundError("Topic not found in this curriculum version.")
    return tv


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValidationError("Topic name must not be blank.")
    if len(cleaned) > MAX_NAME:
        raise ValidationError(f"Topic name must be at most {MAX_NAME} characters.")
    return cleaned


def _clean_outcomes(outcomes: Sequence[str]) -> list[str]:
    cleaned = [o.strip() for o in outcomes]
    if not cleaned or any(not o for o in cleaned):
        raise ValidationError("A Topic needs at least one non-blank learning outcome.")
    return cleaned


def _clean_hours(hours: float | Decimal) -> Decimal:
    value = Decimal(str(hours))
    if value <= 0:
        raise ValidationError("Estimated hours must be greater than zero.")
    if value > 1000:
        raise ValidationError("Estimated hours must be at most 1000.")
    return value.quantize(Decimal("0.01"))


def _unit_of_subject(db: Session, cv: CurriculumVersion, unit_id: uuid.UUID) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None or unit.subject_id != cv.subject_id:
        raise ValidationError("Unit does not belong to this Subject.")
    return unit


# --------------------------------------------------------------------- edits


def update_topic(
    db: Session,
    *,
    actor: User,
    curriculum_version_id: uuid.UUID,
    topic_id: uuid.UUID,
    changes: dict,
    embedder: Embedder,
) -> CurriculumVersion:
    """Rename / classify / hours / outcomes / Bloom / assign Unit. Only the keys present change."""
    allowed = {"name", "classification", "est_hours", "outcomes", "bloom_level", "unit_id"}
    unknown = set(changes) - allowed
    if unknown or not changes:
        raise ValidationError("Provide at least one valid field to change.")
    nulls = sorted(k for k, v in changes.items() if v is None)
    if nulls:  # finding D2: never dereference a null (was a 500); the API rejects it first
        raise ValidationError(f"Fields cannot be null: {', '.join(nulls)}.")
    cv = _open_for_edit(db, actor, curriculum_version_id)
    tv = _tv(db, cv, topic_id)
    before = {
        "name": tv.name,
        "classification": tv.classification.value,
        "est_hours": str(tv.est_hours),
        "bloom_level": tv.bloom_level.value,
        "unit_id": str(tv.unit_id) if tv.unit_id else None,
        "outcomes": list(tv.outcomes),
    }
    if "name" in changes:
        new_name = _clean_name(changes["name"])
        if new_name != tv.name:
            db.add(
                TopicMapping(
                    curriculum_version_id=cv.id,
                    kind=MappingKind.RENAME,
                    from_topic_id=tv.topic_id,
                    to_topic_id=tv.topic_id,  # a rename keeps the stable id
                    created_by=actor.id,
                )
            )
            tv.name = new_name
    if "classification" in changes:
        try:
            tv.classification = TopicClassification(changes["classification"])
        except ValueError:
            raise ValidationError("Classification must be CORE, OPTIONAL or SELF_STUDY.") from None
    if "bloom_level" in changes:
        try:
            tv.bloom_level = BloomLevel(changes["bloom_level"])
        except ValueError:
            raise ValidationError("Invalid Bloom level.") from None
    if "est_hours" in changes:
        tv.est_hours = _clean_hours(changes["est_hours"])
    if "outcomes" in changes:
        tv.outcomes = _clean_outcomes(changes["outcomes"])
    if "unit_id" in changes and changes["unit_id"] != tv.unit_id:
        unit = _unit_of_subject(db, cv, changes["unit_id"])
        top = max(
            (
                r.order_index
                for r in db.scalars(
                    select(TopicVersion).where(
                        TopicVersion.curriculum_version_id == cv.id, TopicVersion.unit_id == unit.id
                    )
                )
            ),
            default=0,
        )
        tv.unit_id = unit.id
        tv.order_index = top + 1
    db.flush()
    after = {
        "name": tv.name,
        "classification": tv.classification.value,
        "est_hours": str(tv.est_hours),
        "bloom_level": tv.bloom_level.value,
        "unit_id": str(tv.unit_id) if tv.unit_id else None,
        "outcomes": list(tv.outcomes),
    }
    return _finish(
        db, cv, actor=actor, embedder=embedder, action="EDIT_CURRICULUM_TOPIC", before=before, after=after
    )


def merge_topics(
    db: Session,
    *,
    actor: User,
    curriculum_version_id: uuid.UUID,
    topic_ids: Sequence[uuid.UUID],
    target_topic_id: uuid.UUID,
    name: str | None,
    embedder: Embedder,
) -> CurriculumVersion:
    """Merge Topics into `target_topic_id`: outcomes are united, hours summed, source chunks and
    edges remapped to the target, lineage kept as MERGE mappings (old id -> target id)."""
    ids = list(dict.fromkeys(topic_ids))
    if len(ids) < 2 or target_topic_id not in ids:
        raise ValidationError("Choose at least two Topics, including the Topic to keep.")
    cv = _open_for_edit(db, actor, curriculum_version_id)
    target = _tv(db, cv, target_topic_id)
    others = [_tv(db, cv, i) for i in ids if i != target_topic_id]
    merged_outcomes = list(target.outcomes)
    hours = Decimal(str(target.est_hours))
    for tv in others:
        for outcome in tv.outcomes:
            if outcome not in merged_outcomes:
                merged_outcomes.append(outcome)
        hours += Decimal(str(tv.est_hours))
    existing_chunks = {
        c
        for (c,) in db.execute(
            select(TopicSourceChunk.content_chunk_id).where(TopicSourceChunk.topic_version_id == target.id)
        )
    }
    for tv in others:
        for (chunk_id,) in db.execute(
            select(TopicSourceChunk.content_chunk_id).where(TopicSourceChunk.topic_version_id == tv.id)
        ).all():
            if chunk_id not in existing_chunks:
                db.add(TopicSourceChunk(topic_version_id=target.id, content_chunk_id=chunk_id))
                existing_chunks.add(chunk_id)
        db.add(
            TopicMapping(
                curriculum_version_id=cv.id,
                kind=MappingKind.MERGE,
                from_topic_id=tv.topic_id,
                to_topic_id=target.topic_id,
                created_by=actor.id,
            )
        )
    source_ids = {tv.topic_id for tv in others}
    before = {"topics": [str(i) for i in ids]}

    edges = list(db.scalars(select(TopicPrereq).where(TopicPrereq.curriculum_version_id == cv.id)))
    by_key = {(e.topic_id, e.prereq_topic_id): e for e in edges}
    to_delete: list[TopicPrereq] = []
    to_update: list[tuple[TopicPrereq, uuid.UUID, uuid.UUID]] = []
    for e in edges:
        new_t = target.topic_id if e.topic_id in source_ids else e.topic_id
        new_p = target.topic_id if e.prereq_topic_id in source_ids else e.prereq_topic_id
        if (new_t, new_p) == (e.topic_id, e.prereq_topic_id):
            continue
        if new_t == new_p:
            to_delete.append(e)
            by_key.pop((e.topic_id, e.prereq_topic_id), None)
            continue
        clash = by_key.get((new_t, new_p))
        if clash is not None and clash is not e:
            if Decimal(str(e.confidence)) > Decimal(str(clash.confidence)):
                clash.confidence = e.confidence
            to_delete.append(e)
            by_key.pop((e.topic_id, e.prereq_topic_id), None)
        else:
            by_key.pop((e.topic_id, e.prereq_topic_id), None)
            by_key[(new_t, new_p)] = e
            to_update.append((e, new_t, new_p))
    for e in to_delete:
        db.delete(e)
    db.flush()
    for e, new_t, new_p in to_update:
        e.topic_id, e.prereq_topic_id = new_t, new_p
    db.flush()

    target.outcomes = merged_outcomes
    target.est_hours = _clean_hours(hours)
    if name is not None:
        target.name = _clean_name(name)
    for tv in others:
        db.delete(tv)
    db.flush()
    return _finish(
        db,
        cv,
        actor=actor,
        embedder=embedder,
        action="MERGE_CURRICULUM_TOPICS",
        before=before,
        after={"kept": str(target.topic_id), "merged": [str(t) for t in source_ids]},
    )


def split_topic(
    db: Session,
    *,
    actor: User,
    curriculum_version_id: uuid.UUID,
    topic_id: uuid.UUID,
    parts: Sequence[SplitPart],
    embedder: Embedder,
) -> CurriculumVersion:
    """Split one Topic into new Topics (new stable ids; SPLIT mappings old -> each part). The
    original's edges are removed; each part states its prerequisites and dependents explicitly."""
    if len(parts) < 2:
        raise ValidationError("A split needs at least two parts.")
    cv = _open_for_edit(db, actor, curriculum_version_id)
    original = _tv(db, cv, topic_id)
    in_version = {
        t
        for (t,) in db.execute(
            select(TopicVersion.topic_id).where(TopicVersion.curriculum_version_id == cv.id)
        )
    }
    for p in parts:
        for other in [*p.prereq_topic_ids, *p.dependent_topic_ids]:
            if other not in in_version or other == topic_id:
                raise ValidationError("Edges of a split part must point at other Topics of this curriculum.")
    original_chunks = [
        c
        for (c,) in db.execute(
            select(TopicSourceChunk.content_chunk_id).where(TopicSourceChunk.topic_version_id == original.id)
        )
    ]
    default_hours = Decimal(str(original.est_hours)) / len(parts)
    base_order = original.order_index * 1000
    created: list[tuple[Topic, TopicVersion, SplitPart]] = []
    for i, part in enumerate(parts, start=1):
        topic = Topic(subject_id=cv.subject_id)
        db.add(topic)
        db.flush()
        tv = TopicVersion(
            topic_id=topic.id,
            curriculum_version_id=cv.id,
            unit_id=original.unit_id,
            name=_clean_name(part.name),
            outcomes=_clean_outcomes(part.outcomes if part.outcomes is not None else original.outcomes),
            bloom_level=original.bloom_level,
            est_hours=_clean_hours(
                part.est_hours if part.est_hours is not None else max(default_hours, Decimal("0.01"))
            ),
            classification=original.classification,
            order_index=base_order + i,
        )
        db.add(tv)
        db.flush()
        for chunk_id in original_chunks:
            db.add(TopicSourceChunk(topic_version_id=tv.id, content_chunk_id=chunk_id))
        db.add(
            TopicMapping(
                curriculum_version_id=cv.id,
                kind=MappingKind.SPLIT,
                from_topic_id=original.topic_id,
                to_topic_id=topic.id,
                created_by=actor.id,
            )
        )
        created.append((topic, tv, part))
    db.execute(
        delete(TopicPrereq).where(
            TopicPrereq.curriculum_version_id == cv.id,
            (TopicPrereq.topic_id == topic_id) | (TopicPrereq.prereq_topic_id == topic_id),
        )
    )
    db.flush()
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for topic, _tv_row, part in created:
        pairs = [(topic.id, p) for p in part.prereq_topic_ids] + [
            (d, topic.id) for d in part.dependent_topic_ids
        ]
        for t_id, p_id in pairs:
            if (t_id, p_id) in seen:
                continue
            seen.add((t_id, p_id))
            existing = db.scalar(
                select(TopicPrereq.id).where(
                    TopicPrereq.curriculum_version_id == cv.id,
                    TopicPrereq.topic_id == t_id,
                    TopicPrereq.prereq_topic_id == p_id,
                )
            )
            if existing is None:
                db.add(
                    TopicPrereq(
                        curriculum_version_id=cv.id,
                        topic_id=t_id,
                        prereq_topic_id=p_id,
                        confidence=Decimal("1.000"),
                        source=EdgeSource.TEACHER,
                        approved_by_teacher=True,
                        dropped=False,
                    )
                )
    db.delete(original)
    db.flush()
    return _finish(
        db,
        cv,
        actor=actor,
        embedder=embedder,
        action="SPLIT_CURRICULUM_TOPIC",
        before={"topic": str(topic_id)},
        after={"parts": [str(t.id) for t, _, _ in created]},
    )


def reorder_unit_topics(
    db: Session,
    *,
    actor: User,
    curriculum_version_id: uuid.UUID,
    unit_id: uuid.UUID,
    ordered_topic_ids: Sequence[uuid.UUID],
    embedder: Embedder,
) -> CurriculumVersion:
    cv = _open_for_edit(db, actor, curriculum_version_id)
    _unit_of_subject(db, cv, unit_id)
    rows = list(
        db.scalars(
            select(TopicVersion).where(
                TopicVersion.curriculum_version_id == cv.id, TopicVersion.unit_id == unit_id
            )
        )
    )
    if sorted(map(str, ordered_topic_ids)) != sorted(str(r.topic_id) for r in rows):
        raise ValidationError("The new order must list exactly the Topics currently in this Unit.")
    before = {"order": [str(r.topic_id) for r in sorted(rows, key=lambda r: r.order_index)]}
    position = {tid: i for i, tid in enumerate(ordered_topic_ids, start=1)}
    for r in rows:
        r.order_index = position[r.topic_id]
    db.flush()
    return _finish(
        db,
        cv,
        actor=actor,
        embedder=embedder,
        action="REORDER_CURRICULUM_TOPICS",
        before=before,
        after={"order": [str(t) for t in ordered_topic_ids], "unit_id": str(unit_id)},
    )


def add_edge(
    db: Session,
    *,
    actor: User,
    curriculum_version_id: uuid.UUID,
    topic_id: uuid.UUID,
    prereq_topic_id: uuid.UUID,
    confidence: float,
    prereq_curriculum_version_id: uuid.UUID | None,
    embedder: Embedder,
) -> CurriculumVersion:
    """Add a prerequisite edge `topic_id requires prereq_topic_id`. A cross-subject target must
    be in an ACTIVE version of an earlier-semester Subject of the same Program (plan A-6); the
    edge pins that exact version. A cycle the edge creates is resolved by validation."""
    if topic_id == prereq_topic_id:
        raise ValidationError("A Topic cannot be its own prerequisite.")
    conf = Decimal(str(confidence))
    if not Decimal(0) <= conf <= Decimal(1):
        raise ValidationError("Confidence must be between 0 and 1.")
    cv = _open_for_edit(db, actor, curriculum_version_id)
    _tv(db, cv, topic_id)
    internal = db.scalar(
        select(TopicVersion.id).where(
            TopicVersion.curriculum_version_id == cv.id, TopicVersion.topic_id == prereq_topic_id
        )
    )
    pinned: uuid.UUID | None = None
    if internal is not None:
        if prereq_curriculum_version_id is not None:
            raise ValidationError("An edge inside this Subject must not name another curriculum version.")
    else:
        if prereq_curriculum_version_id is None:
            raise NotFoundError("Prerequisite Topic not found in this curriculum version.")
        subject = db.get(Subject, cv.subject_id)
        assert subject is not None
        offered = {
            (row.topic_id, row.curriculum_version_id) for row in cs.offered_external_topics(db, subject)
        }
        if (prereq_topic_id, prereq_curriculum_version_id) not in offered:
            raise ValidationError(
                "A cross-subject prerequisite must be a Topic of an ACTIVE curriculum of an "
                "earlier-semester Subject in the same Program."
            )
        pinned = prereq_curriculum_version_id
    if db.scalar(
        select(TopicPrereq.id).where(
            TopicPrereq.curriculum_version_id == cv.id,
            TopicPrereq.topic_id == topic_id,
            TopicPrereq.prereq_topic_id == prereq_topic_id,
        )
    ):
        raise ConflictError("This prerequisite edge already exists.")
    edge = TopicPrereq(
        curriculum_version_id=cv.id,
        topic_id=topic_id,
        prereq_topic_id=prereq_topic_id,
        prereq_curriculum_version_id=pinned,
        confidence=conf.quantize(Decimal("0.001")),
        source=EdgeSource.TEACHER,
        approved_by_teacher=True,
        dropped=False,
    )
    db.add(edge)
    db.flush()
    return _finish(
        db,
        cv,
        actor=actor,
        embedder=embedder,
        action="ADD_CURRICULUM_EDGE",
        before=None,
        after={
            "edge_id": str(edge.id),
            "topic_id": str(topic_id),
            "prereq_topic_id": str(prereq_topic_id),
            "confidence": str(edge.confidence),
            "prereq_curriculum_version_id": str(pinned) if pinned else None,
        },
    )


def delete_edge(
    db: Session, *, actor: User, curriculum_version_id: uuid.UUID, edge_id: uuid.UUID, embedder: Embedder
) -> CurriculumVersion:
    cv = _open_for_edit(db, actor, curriculum_version_id)
    edge = db.get(TopicPrereq, edge_id)
    if edge is None or edge.curriculum_version_id != cv.id:
        raise NotFoundError("Edge not found in this curriculum version.")
    before = {
        "edge_id": str(edge.id),
        "topic_id": str(edge.topic_id),
        "prereq_topic_id": str(edge.prereq_topic_id),
        "confidence": str(edge.confidence),
        "dropped": edge.dropped,
    }
    db.delete(edge)
    db.flush()
    return _finish(
        db, cv, actor=actor, embedder=embedder, action="DELETE_CURRICULUM_EDGE", before=before, after=None
    )


def delete_topic(
    db: Session, *, actor: User, curriculum_version_id: uuid.UUID, topic_id: uuid.UUID, embedder: Embedder
) -> CurriculumVersion:
    """Remove a Topic and every edge that touches it (also how an orphan is resolved, A-5)."""
    cv = _open_for_edit(db, actor, curriculum_version_id)
    tv = _tv(db, cv, topic_id)
    before = {"topic_id": str(topic_id), "name": tv.name}
    db.execute(
        delete(TopicPrereq).where(
            TopicPrereq.curriculum_version_id == cv.id,
            (TopicPrereq.topic_id == topic_id) | (TopicPrereq.prereq_topic_id == topic_id),
        )
    )
    db.delete(tv)
    db.flush()
    return _finish(
        db, cv, actor=actor, embedder=embedder, action="DELETE_CURRICULUM_TOPIC", before=before, after=None
    )


__all__ = [
    "EDIT_STATE_MESSAGE",
    "SplitPart",
    "add_edge",
    "delete_edge",
    "delete_topic",
    "merge_topics",
    "reorder_unit_topics",
    "split_topic",
    "update_topic",
]
