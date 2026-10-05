"""Curriculum versions: generation request, persistence of a validated draft, deterministic
validation, Owner approval/rejection/fallback, and reads. FR-CUR-001, FR-CUR-002, FR-CUR-004
(BUS-020..023, BUS-037, BUS-043, BUS-050).

Deterministic and LLM-free (`.claude/rules/deterministic-services.md`): the Curriculum Agent
(`app.agents`) only produces a draft that is handed to `persist_draft`; this module never calls
a model and never imports `langchain*`, `anthropic`, `app.agents` or `app.prompts`. Embeddings
come from an injected `Embedder` port (a local model, not an LLM).

Authorization (plan A-1), always at query level:
- assigned Teacher = TeacherAssignment on any SubjectInstance of the Subject; not assigned -> 404.
- Subject Owner = SubjectOwnerAssignment.owner_teacher_id; assigned non-Owner -> 403 (BUS-043).

A DRAFT version is a mutable working copy with a `revision` counter (plan A-4). Approval needs
`validated_revision == revision`, so any edit invalidates a previous validation until the
automatic re-run finishes. ACTIVE versions are immutable (every edit path checks the status).
ADR-0011: every mutation writes an audit row in the same transaction.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.ai import AgentRun, AgentRunStatus
from app.models.content import (
    ContentAsset,
    ContentChunk,
    ContentType,
    ContentVersion,
    ContentVersionStatus,
    IngestionStatus,
)
from app.models.curriculum import (
    BloomLevel,
    CurriculumOrigin,
    CurriculumStatus,
    CurriculumVersion,
    EdgeSource,
    FlagKind,
    GraphValidationFlag,
    SimilarityThreshold,
    Topic,
    TopicClassification,
    TopicMapping,
    TopicPrereq,
    TopicSourceChunk,
    TopicVersion,
    ValidationStatus,
)
from app.models.embedding_config import EmbeddingConfig
from app.models.subject import Subject, Unit
from app.models.user import User
from app.schemas.curriculum_agent import EXTERNAL_REF_PREFIX, CurriculumDraft
from app.services import audit
from app.services import curriculum_graph as graph
from app.services import similarity_config_service as thresholds
from app.services.content_service import (
    _log_denied,
    is_owner,
    require_assigned,
    require_owner,
)
from app.services.embedding_config_service import get_or_create_active_config
from app.services.ingestion.ports import Embedder

logger = logging.getLogger(__name__)

NOT_FOUND_VERSION = "Curriculum version not found, or not assigned to this Teacher."
EDITABLE_STATUSES = (CurriculumStatus.DRAFT, CurriculumStatus.RETURNED)
CYCLE_BANNER = "A prerequisite cycle was detected. Review the flagged relationship."  # Section 37


class CurriculumQueue(Protocol):
    def enqueue(self, curriculum_version_id: str) -> None: ...


# ------------------------------------------------------------------ helpers


def version_for_teacher(db: Session, teacher: User, curriculum_version_id: uuid.UUID) -> CurriculumVersion:
    """The version if the Teacher is assigned to its Subject; otherwise a non-enumerating 404."""
    cv = db.get(CurriculumVersion, curriculum_version_id)
    if cv is None:
        _log_denied(teacher, "curriculum_version_missing", curriculum_version_id=curriculum_version_id)
        raise NotFoundError(NOT_FOUND_VERSION)
    try:
        require_assigned(db, teacher, cv.subject_id)
    except NotFoundError:
        raise NotFoundError(NOT_FOUND_VERSION) from None
    return cv


def lock_version(db: Session, curriculum_version_id: uuid.UUID) -> CurriculumVersion:
    return db.execute(
        select(CurriculumVersion)
        .where(CurriculumVersion.id == curriculum_version_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()


def lock_subject(db: Session, subject_id: uuid.UUID) -> None:
    """Serialises version numbering and active-pointer swaps per Subject."""
    db.execute(select(Subject.id).where(Subject.id == subject_id).with_for_update())


def _next_version_no(db: Session, subject_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.max(CurriculumVersion.version_no)).where(CurriculumVersion.subject_id == subject_id)
        )
        or 0
    ) + 1


def topic_text(name: str, outcomes: Sequence[str]) -> str:
    return name.strip() + "\n" + "\n".join(o.strip() for o in outcomes)


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------- generation (FR-CUR-001)


def active_syllabus_version(db: Session, subject_id: uuid.UUID) -> ContentVersion | None:
    return db.scalar(
        select(ContentVersion)
        .join(ContentAsset, ContentAsset.id == ContentVersion.content_asset_id)
        .where(
            ContentAsset.subject_id == subject_id,
            ContentAsset.content_type == ContentType.SYLLABUS,
            ContentVersion.status == ContentVersionStatus.ACTIVE,
            ContentVersion.ingestion_status == IngestionStatus.SUCCEEDED,
        )
    )


def request_generation(
    db: Session, *, actor: User, subject_id: uuid.UUID, queue: CurriculumQueue
) -> CurriculumVersion:
    """Any assigned Teacher requests generation. Creates a GENERATING version and queues the
    worker; the current ACTIVE curriculum is untouched. Needs an ACTIVE, ingested syllabus.
    LAB Subjects are allowed (plan A-7)."""
    require_assigned(db, actor, subject_id)
    syllabus = active_syllabus_version(db, subject_id)
    if syllabus is None:
        raise ConflictError(
            "This Subject has no active, successfully ingested syllabus. "
            "Ask the Subject Owner to activate a syllabus first."
        )
    lock_subject(db, subject_id)
    in_flight = db.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.subject_id == subject_id,
            CurriculumVersion.status == CurriculumStatus.GENERATING,
        )
    )
    if in_flight is not None:
        available_at = generation_stale_at(db, in_flight)
        if datetime.now(UTC) < available_at:
            raise ConflictError(
                "A curriculum is already being generated for this Subject. If it stays stuck, "
                f"you can request a new one after {available_at.isoformat()}."
            )
        # Finding D1: a GENERATING version with no activity past the window is presumed dead.
        mark_generation_failed(db, in_flight.id, STALE_GENERATION_MESSAGE)
        lock_subject(db, subject_id)
    cv = CurriculumVersion(
        subject_id=subject_id,
        version_no=_next_version_no(db, subject_id),
        status=CurriculumStatus.GENERATING,
        origin=CurriculumOrigin.AGENT,
        source_content_version_id=syllabus.id,
        revision=1,
        validation_status=ValidationStatus.NOT_RUN,
        created_by=actor.id,
    )
    db.add(cv)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="REQUEST_CURRICULUM_GENERATION",
        entity_type="curriculum_version",
        entity_id=cv.id,
        after={"subject_id": str(subject_id), "source_content_version_id": str(syllabus.id)},
    )
    db.commit()
    try:
        queue.enqueue(str(cv.id))
    except Exception:  # noqa: BLE001 - never leave a version GENERATING with no job (finding D1)
        logger.exception("Could not queue curriculum generation for %s", cv.id)
        cv = mark_generation_failed(db, cv.id, QUEUE_FAILED_MESSAGE)
    return cv


STALE_GENERATION_MESSAGE = (
    "Curriculum generation stopped responding and was marked failed. Request it again, or ask the "
    "Subject Owner to activate the flat Unit-order fallback."
)
QUEUE_FAILED_MESSAGE = (
    "Curriculum generation could not be queued. Request it again later, or ask the Subject Owner to "
    "activate the flat Unit-order fallback."
)


def generation_stale_at(db: Session, cv: CurriculumVersion) -> datetime:
    """When a GENERATING version counts as stuck: its last activity (the version row or any of its
    agent runs) plus the configured window (finding D1)."""
    last_run = db.scalar(
        select(func.max(func.coalesce(AgentRun.finished_at, AgentRun.started_at))).where(
            AgentRun.curriculum_version_id == cv.id
        )
    )
    activity = max(t for t in (cv.updated_at, cv.created_at, last_run) if t is not None)
    if activity.tzinfo is None:
        activity = activity.replace(tzinfo=UTC)
    return activity + timedelta(seconds=settings.effective_curriculum_stale_after_seconds)


def mark_generation_failed(
    db: Session, curriculum_version_id: uuid.UUID, message: str, *, agent_run_id: uuid.UUID | None = None
) -> CurriculumVersion:
    cv = lock_version(db, curriculum_version_id)
    if cv.status != CurriculumStatus.GENERATING:
        return cv
    cv.status = CurriculumStatus.GENERATION_FAILED
    cv.failure_message = message[:1000]
    if agent_run_id is not None:
        cv.agent_run_id = agent_run_id
    # Close any run left RUNNING by a crashed or stopped worker (finding D1, NFR-AI-002).
    now = datetime.now(UTC)
    for run in db.scalars(
        select(AgentRun).where(
            AgentRun.curriculum_version_id == cv.id, AgentRun.status == AgentRunStatus.RUNNING
        )
    ):
        run.status = AgentRunStatus.FAILED
        run.error = message[:1000]
        run.finished_at = now
    audit.record(
        db,
        actor=None,
        action="CURRICULUM_GENERATION_FAILED",
        entity_type="curriculum_version",
        entity_id=cv.id,
        after={"message": cv.failure_message},
    )
    db.commit()
    return cv


@dataclass(frozen=True)
class ExternalTopicRow:
    topic_id: uuid.UUID
    name: str
    subject_id: uuid.UUID
    subject_code: str
    semester_no: int
    curriculum_version_id: uuid.UUID

    @property
    def ref(self) -> str:
        return f"{EXTERNAL_REF_PREFIX}{self.topic_id}"


def offered_external_topics(db: Session, subject: Subject) -> list[ExternalTopicRow]:
    """Plan A-6: Topics of an ACTIVE CurriculumVersion of an earlier-semester Subject of the
    same Program. Anything else can never be a cross-subject prerequisite."""
    rows = db.execute(
        select(TopicVersion, Subject, CurriculumVersion)
        .join(CurriculumVersion, CurriculumVersion.id == TopicVersion.curriculum_version_id)
        .join(Subject, Subject.id == CurriculumVersion.subject_id)
        .where(
            CurriculumVersion.status == CurriculumStatus.ACTIVE,
            Subject.program_id == subject.program_id,
            Subject.id != subject.id,
        )
        .order_by(Subject.semester_no, Subject.code, TopicVersion.order_index)
    ).all()
    result = []
    for tv, subj, cv in rows:
        if graph.cross_subject_scope_allowed(
            current_semester=subject.semester_no, target_semester=subj.semester_no, same_program=True
        ):
            result.append(ExternalTopicRow(tv.topic_id, tv.name, subj.id, subj.code, subj.semester_no, cv.id))
    return result


@dataclass
class GenerationInputs:
    subject: Subject
    units: list[Unit]
    chunks: list[ContentChunk]
    external_topics: list[ExternalTopicRow]
    prior_topics: list[tuple[uuid.UUID, str]]  # (stable topic id, name) of the current ACTIVE graph
    content_version_id: uuid.UUID


def load_generation_inputs(db: Session, curriculum_version_id: uuid.UUID) -> GenerationInputs:
    cv = db.get(CurriculumVersion, curriculum_version_id)
    if cv is None or cv.source_content_version_id is None:
        raise NotFoundError(NOT_FOUND_VERSION)
    subject = db.get(Subject, cv.subject_id)
    assert subject is not None
    units = list(db.scalars(select(Unit).where(Unit.subject_id == subject.id).order_by(Unit.order_index)))
    chunks = list(
        db.scalars(
            select(ContentChunk)
            .where(
                ContentChunk.subject_id == subject.id,
                ContentChunk.content_version_id == cv.source_content_version_id,
            )
            .order_by(ContentChunk.chunk_index)
        )
    )
    active = db.scalar(
        select(CurriculumVersion.id).where(
            CurriculumVersion.subject_id == subject.id, CurriculumVersion.status == CurriculumStatus.ACTIVE
        )
    )
    prior: list[tuple[uuid.UUID, str]] = []
    if active is not None:
        prior = [
            (tv.topic_id, tv.name)
            for tv in db.scalars(
                select(TopicVersion)
                .where(TopicVersion.curriculum_version_id == active)
                .order_by(TopicVersion.order_index)
            )
        ]
    return GenerationInputs(
        subject=subject,
        units=units,
        chunks=chunks,
        external_topics=offered_external_topics(db, subject),
        prior_topics=prior,
        content_version_id=cv.source_content_version_id,
    )


def persist_draft(
    db: Session,
    curriculum_version_id: uuid.UUID,
    draft: CurriculumDraft,
    *,
    agent_run_id: uuid.UUID,
) -> CurriculumVersion:
    """Turn a schema-valid agent draft into DRAFT Topics/edges. Does not commit (the caller
    validates and commits in one transaction). Cross-subject edges outside the offered scope are
    skipped and recorded as SCOPE_VIOLATION flags."""
    cv = lock_version(db, curriculum_version_id)
    if cv.status != CurriculumStatus.GENERATING:
        return cv
    subject = db.get(Subject, cv.subject_id)
    assert subject is not None
    units = {u.order_index: u for u in db.scalars(select(Unit).where(Unit.subject_id == subject.id))}
    offered = {row.ref: row for row in offered_external_topics(db, subject)}
    prior_ids = {
        tid
        for (tid,) in db.execute(
            select(TopicVersion.topic_id)
            .join(CurriculumVersion, CurriculumVersion.id == TopicVersion.curriculum_version_id)
            .where(
                CurriculumVersion.subject_id == subject.id,
                CurriculumVersion.status == CurriculumStatus.ACTIVE,
            )
        )
    }
    chunk_ids_in_source = {
        cid
        for (cid,) in db.execute(
            select(ContentChunk.id).where(ContentChunk.content_version_id == cv.source_content_version_id)
        )
    }

    topic_by_key: dict[str, uuid.UUID] = {}
    used_prior: set[uuid.UUID] = set()
    per_unit_counter: dict[uuid.UUID, int] = {}
    version_rows: dict[str, TopicVersion] = {}
    for dt in draft.topics:
        unit = units[dt.unit_order]
        if (
            dt.prior_topic_id is not None
            and dt.prior_topic_id in prior_ids
            and dt.prior_topic_id not in used_prior
        ):
            topic_id = dt.prior_topic_id
            used_prior.add(topic_id)
        else:
            topic = Topic(subject_id=subject.id)
            db.add(topic)
            db.flush()
            topic_id = topic.id
        topic_by_key[dt.key] = topic_id
        per_unit_counter[unit.id] = per_unit_counter.get(unit.id, 0) + 1
        tv = TopicVersion(
            topic_id=topic_id,
            curriculum_version_id=cv.id,
            unit_id=unit.id,
            name=dt.name,
            outcomes=list(dt.outcomes),
            bloom_level=dt.bloom_level,
            est_hours=Decimal(str(dt.est_hours)),
            classification=dt.classification,
            order_index=per_unit_counter[unit.id],
        )
        db.add(tv)
        version_rows[dt.key] = tv
    db.flush()

    for dt in draft.topics:
        tv = version_rows[dt.key]
        for chunk_id in dict.fromkeys(dt.source_chunk_ids):
            if chunk_id in chunk_ids_in_source:
                db.add(TopicSourceChunk(topic_version_id=tv.id, content_chunk_id=chunk_id))
        for de in dt.prerequisites:
            if de.prereq_ref in topic_by_key:
                db.add(
                    TopicPrereq(
                        curriculum_version_id=cv.id,
                        topic_id=tv.topic_id,
                        prereq_topic_id=topic_by_key[de.prereq_ref],
                        confidence=Decimal(str(round(de.confidence, 3))),
                        source=EdgeSource.AGENT,
                        approved_by_teacher=False,
                        dropped=False,
                    )
                )
            elif de.prereq_ref in offered:
                ext = offered[de.prereq_ref]
                db.add(
                    TopicPrereq(
                        curriculum_version_id=cv.id,
                        topic_id=tv.topic_id,
                        prereq_topic_id=ext.topic_id,
                        prereq_curriculum_version_id=ext.curriculum_version_id,
                        confidence=Decimal(str(round(de.confidence, 3))),
                        source=EdgeSource.AGENT,
                        approved_by_teacher=False,
                        dropped=False,
                    )
                )
            else:
                db.add(
                    GraphValidationFlag(
                        curriculum_version_id=cv.id,
                        revision=cv.revision,
                        kind=FlagKind.SCOPE_VIOLATION,
                        topic_id=tv.topic_id,
                        detail={
                            "prereq_ref": de.prereq_ref,
                            "reason": "Cross-subject prerequisite is not in an ACTIVE earlier-semester "
                            "Subject of the same Program; the edge was not stored.",
                        },
                        blocking=False,
                    )
                )
    try:
        db.flush()
    except Exception as exc:  # duplicate (topic, prereq) pairs in the same draft, etc.
        raise ValidationError(f"The generated curriculum could not be stored: {type(exc).__name__}") from exc

    cv.status = CurriculumStatus.DRAFT
    cv.agent_run_id = agent_run_id
    cv.failure_message = None
    audit.record(
        db,
        actor=None,
        action="CURRICULUM_DRAFT_CREATED",
        entity_type="curriculum_version",
        entity_id=cv.id,
        after={"topics": len(draft.topics), "agent_run_id": str(agent_run_id)},
    )
    db.flush()  # later steps re-read the row with a lock; unflushed changes would be discarded
    return cv


# --------------------------------------------------------- validation (FR-CUR-002)


@dataclass
class ValidationSummary:
    revision: int
    passed: bool
    dropped_edges: int
    orphans: int
    duplicates: int
    blocking_reasons: list[str] = field(default_factory=list)
    banner: str | None = None


def _topic_versions(db: Session, cv_id: uuid.UUID) -> list[TopicVersion]:
    return list(
        db.scalars(
            select(TopicVersion)
            .where(TopicVersion.curriculum_version_id == cv_id)
            .order_by(TopicVersion.unit_id, TopicVersion.order_index, TopicVersion.id)
        )
    )


def _edge_in(edge: TopicPrereq) -> graph.EdgeIn:
    return graph.EdgeIn(
        edge_key=str(edge.id),
        topic_id=str(edge.topic_id),
        prereq_topic_id=str(edge.prereq_topic_id),
        confidence=Decimal(str(edge.confidence)),
    )


def validate_version(
    db: Session,
    curriculum_version_id: uuid.UUID,
    *,
    embedder: Embedder,
    actor: User | None = None,
    commit: bool = True,
) -> ValidationSummary:
    """Run the deterministic checks (FR-CUR-002) and persist their outcome on a DRAFT/RETURNED
    working copy: dropped cycle edges, orphans, duplicates, embedding/threshold references."""
    config = get_or_create_active_config(db)
    cv = lock_version(db, curriculum_version_id)
    if cv.status not in EDITABLE_STATUSES:
        raise ConflictError("Only a DRAFT curriculum can be validated.")
    threshold = thresholds.resolve_threshold(db, config)

    tvs = _topic_versions(db, cv.id)
    to_embed: list[tuple[TopicVersion, str]] = []
    for tv in tvs:
        text = topic_text(tv.name, tv.outcomes)
        sha = _text_sha(text)
        if tv.embedding is None or tv.embedding_config_id != config.id or tv.embedding_text_sha256 != sha:
            to_embed.append((tv, text))
    if to_embed:
        vectors = embedder.embed([t for _, t in to_embed])
        if len(vectors) != len(to_embed):
            raise ValidationError("The embedder returned the wrong number of vectors.")
        for (tv, text), vec in zip(to_embed, vectors, strict=True):
            tv.embedding = list(vec)
            tv.embedding_config_id = config.id
            tv.embedding_text_sha256 = _text_sha(text)
        db.flush()

    edges = list(db.scalars(select(TopicPrereq).where(TopicPrereq.curriculum_version_id == cv.id)))
    live = [e for e in edges if not e.dropped]
    verdict = graph.validate_graph(
        topics=[graph.TopicIn(str(tv.topic_id), str(tv.unit_id) if tv.unit_id else None) for tv in tvs],
        edges=[_edge_in(e) for e in live],
        vectors=[
            graph.VectorItem(str(tv.topic_id), str(tv.embedding_config_id), [float(x) for x in tv.embedding])
            for tv in tvs
            if tv.embedding is not None and tv.embedding_config_id is not None
        ],
        threshold=Decimal(str(threshold.value)),
    )

    edge_by_key = {str(e.id): e for e in edges}
    for dropped in verdict.dropped:
        row = edge_by_key[str(dropped.edge.edge_key)]
        row.dropped = True
        row.drop_reason = dropped.reason[:500]
    db.flush()

    # Regenerate every flag except SCOPE_VIOLATION (recorded once at generation time).
    db.execute(
        delete(GraphValidationFlag).where(
            GraphValidationFlag.curriculum_version_id == cv.id,
            GraphValidationFlag.kind != FlagKind.SCOPE_VIOLATION,
        )
    )
    db.flush()
    for row in edges:
        if row.dropped:
            db.add(
                GraphValidationFlag(
                    curriculum_version_id=cv.id,
                    revision=cv.revision,
                    kind=FlagKind.CYCLE_EDGE_DROPPED,
                    topic_id=row.topic_id,
                    other_topic_id=row.prereq_topic_id,
                    edge_id=row.id,
                    detail={
                        "confidence": str(row.confidence),
                        "reason": row.drop_reason,
                        "banner": CYCLE_BANNER,
                    },
                    blocking=False,
                )
            )
    for topic_id in verdict.orphans:
        db.add(
            GraphValidationFlag(
                curriculum_version_id=cv.id,
                revision=cv.revision,
                kind=FlagKind.ORPHAN,
                topic_id=uuid.UUID(topic_id),
                detail={"reason": "Topic has no Unit; assign a Unit or remove the Topic."},
                blocking=True,
            )
        )
    for pair in verdict.duplicates:
        db.add(
            GraphValidationFlag(
                curriculum_version_id=cv.id,
                revision=cv.revision,
                kind=FlagKind.DUPLICATE_TOPIC,
                topic_id=uuid.UUID(pair.topic_id),
                other_topic_id=uuid.UUID(pair.other_topic_id),
                detail={
                    "similarity": pair.similarity,
                    "threshold": str(threshold.value),
                    "threshold_id": str(threshold.id),
                    "embedding_config_id": pair.embedding_config_id,
                },
                blocking=False,
            )
        )
    if verdict.remaining_cycle is not None:
        db.add(
            GraphValidationFlag(
                curriculum_version_id=cv.id,
                revision=cv.revision,
                kind=FlagKind.CYCLE_REMAINING,
                detail={"cycle": list(verdict.remaining_cycle)},
                blocking=True,
            )
        )

    cv.embedding_config_id = config.id
    cv.similarity_threshold_id = threshold.id
    cv.validated_revision = cv.revision
    cv.validation_status = ValidationStatus.PASSED if verdict.passed else ValidationStatus.BLOCKED
    audit.record(
        db,
        actor=actor,
        action="VALIDATE_CURRICULUM",
        entity_type="curriculum_version",
        entity_id=cv.id,
        after={
            "revision": cv.revision,
            "passed": verdict.passed,
            "dropped_edges": sum(1 for e in edges if e.dropped),
            "orphans": len(verdict.orphans),
            "duplicates": len(verdict.duplicates),
            "embedding_config_id": str(config.id),
            "threshold_id": str(threshold.id),
        },
    )
    if commit:
        db.commit()
    else:
        db.flush()
    any_dropped = sum(1 for e in edges if e.dropped)
    return ValidationSummary(
        revision=cv.revision,
        passed=verdict.passed,
        dropped_edges=any_dropped,
        orphans=len(verdict.orphans),
        duplicates=len(verdict.duplicates),
        blocking_reasons=list(verdict.blocking_reasons),
        banner=CYCLE_BANNER if any_dropped else None,
    )


def rerun_validation(
    db: Session, *, actor: User, curriculum_version_id: uuid.UUID, embedder: Embedder
) -> ValidationSummary:
    cv = version_for_teacher(db, actor, curriculum_version_id)
    return validate_version(db, cv.id, embedder=embedder, actor=actor)


# --------------------------------------------------------- approval blockers


def approval_blockers(db: Session, cv: CurriculumVersion) -> list[str]:
    """Everything that currently prevents approval (empty list = approvable). Also a
    defence-in-depth recheck of the graph from stored rows, independent of earlier validation."""
    blockers: list[str] = []
    if cv.status != CurriculumStatus.DRAFT:
        return [f"Only a DRAFT curriculum can be approved (this one is {cv.status.value})."]
    if cv.validated_revision != cv.revision or cv.validation_status == ValidationStatus.NOT_RUN:
        blockers.append("Validation is out of date after the latest change; re-run validation.")
    elif cv.validation_status != ValidationStatus.PASSED:
        blockers.append("Validation found blocking problems (orphan Topics or a prerequisite cycle).")
    threshold = (
        db.get(SimilarityThreshold, cv.similarity_threshold_id) if cv.similarity_threshold_id else None
    )
    message = thresholds.threshold_blocker(threshold, cv.embedding_config_id)
    if message:
        blockers.append(message)
    tvs = _topic_versions(db, cv.id)
    if not tvs:
        blockers.append("The curriculum has no Topics.")
    orphans = graph.find_orphans(
        [graph.TopicIn(str(t.topic_id), str(t.unit_id) if t.unit_id else None) for t in tvs]
    )
    if orphans:
        blockers.append(f"{len(orphans)} Topic(s) have no Unit; assign a Unit or remove them.")
    live = [
        _edge_in(e)
        for e in db.scalars(
            select(TopicPrereq).where(
                TopicPrereq.curriculum_version_id == cv.id, TopicPrereq.dropped.is_(False)
            )
        )
    ]
    if graph.has_cycle(live):
        blockers.append("A prerequisite cycle remains in the graph.")
    return list(dict.fromkeys(blockers))


# ------------------------------------------------------ Owner decisions (FR-CUR-004)


def _decision_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    reason = reason.strip()
    if len(reason) > 1000:
        raise ValidationError("Reason must be at most 1000 characters.")
    return reason or None


def approve_version(
    db: Session, *, actor: User, curriculum_version_id: uuid.UUID, reason: str | None
) -> CurriculumVersion:
    """Owner-only. Validated DRAFT -> ACTIVE; the prior ACTIVE becomes SUPERSEDED but stays
    resolvable. The active-pointer swap happens under a Subject row lock in one transaction."""
    reason = _decision_reason(reason)
    cv = version_for_teacher(db, actor, curriculum_version_id)
    require_owner(db, actor, cv.subject_id)
    lock_subject(db, cv.subject_id)
    cv = lock_version(db, cv.id)
    blockers = approval_blockers(db, cv)
    if blockers:
        raise ConflictError(" ".join(blockers))
    previous = db.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.subject_id == cv.subject_id, CurriculumVersion.status == CurriculumStatus.ACTIVE
        )
    )
    if previous is not None:
        previous.status = CurriculumStatus.SUPERSEDED
        db.flush()  # free the one-active-per-subject slot first
        cv.supersedes_version_id = previous.id
    now = datetime.now(UTC)
    cv.status = CurriculumStatus.ACTIVE
    cv.decided_by = actor.id
    cv.decided_at = now
    cv.activated_at = now
    cv.decision_reason = reason
    audit.record(
        db,
        actor=actor,
        action="APPROVE_CURRICULUM",
        entity_type="curriculum_version",
        entity_id=cv.id,
        before={"status": "DRAFT", "previous_active": str(previous.id) if previous else None},
        after={"status": "ACTIVE", "superseded": str(previous.id) if previous else None},
        reason=reason,
    )
    db.commit()
    return cv


def reject_version(
    db: Session, *, actor: User, curriculum_version_id: uuid.UUID, reason: str | None
) -> CurriculumVersion:
    """Owner-only. DRAFT -> RETURNED; the prior ACTIVE curriculum is left untouched (BUS-023)."""
    reason = _decision_reason(reason)
    cv = version_for_teacher(db, actor, curriculum_version_id)
    require_owner(db, actor, cv.subject_id)
    lock_subject(db, cv.subject_id)
    cv = lock_version(db, cv.id)
    if cv.status != CurriculumStatus.DRAFT:
        raise ConflictError("Only a DRAFT curriculum can be rejected.")
    cv.status = CurriculumStatus.RETURNED
    cv.decided_by = actor.id
    cv.decided_at = datetime.now(UTC)
    cv.decision_reason = reason
    audit.record(
        db,
        actor=actor,
        action="REJECT_CURRICULUM",
        entity_type="curriculum_version",
        entity_id=cv.id,
        before={"status": "DRAFT"},
        after={"status": "RETURNED"},
        reason=reason,
    )
    db.commit()
    return cv


def activate_fallback(
    db: Session, *, actor: User, subject_id: uuid.UUID, reason: str | None
) -> CurriculumVersion:
    """Owner-only, explicit, and only when the Subject has no ACTIVE curriculum (BUS-023): a
    recorded flat Unit-order version - one Topic per Unit, no prerequisite edges."""
    reason = _decision_reason(reason)
    require_owner(db, actor, subject_id)
    lock_subject(db, subject_id)
    if db.scalar(
        select(CurriculumVersion.id).where(
            CurriculumVersion.subject_id == subject_id, CurriculumVersion.status == CurriculumStatus.ACTIVE
        )
    ):
        raise ConflictError(
            "This Subject already has an active curriculum; the flat fallback is not allowed."
        )
    units = list(db.scalars(select(Unit).where(Unit.subject_id == subject_id).order_by(Unit.order_index)))
    if not units:
        raise ValidationError("This Subject has no Units to build a flat Unit-order curriculum from.")
    syllabus = active_syllabus_version(db, subject_id)
    now = datetime.now(UTC)
    cv = CurriculumVersion(
        subject_id=subject_id,
        version_no=_next_version_no(db, subject_id),
        status=CurriculumStatus.DRAFT,  # flipped to ACTIVE below, after the Topics exist
        origin=CurriculumOrigin.FLAT_FALLBACK,
        source_content_version_id=syllabus.id if syllabus else None,
        revision=1,
        validation_status=ValidationStatus.NOT_RUN,
        created_by=actor.id,
    )
    db.add(cv)
    db.flush()
    by_id = {str(u.id): u for u in units}
    for spec in graph.build_flat_order(graph.FlatUnit(str(u.id), u.name, u.order_index) for u in units):
        unit = by_id[spec.unit_id]
        topic = Topic(subject_id=subject_id)
        db.add(topic)
        db.flush()
        db.add(
            TopicVersion(
                topic_id=topic.id,
                curriculum_version_id=cv.id,
                unit_id=unit.id,
                name=spec.name,
                outcomes=[f"Cover the syllabus content of {unit.name}."],
                bloom_level=BloomLevel.UNDERSTAND,
                est_hours=Decimal(str(settings.fallback_topic_est_hours)),
                classification=TopicClassification.CORE,
                order_index=spec.order_index,
            )
        )
    db.flush()
    cv.status = CurriculumStatus.ACTIVE
    cv.validated_revision = 1
    cv.validation_status = ValidationStatus.PASSED  # no edges, every Topic has its Unit
    cv.decided_by = actor.id
    cv.decided_at = now
    cv.activated_at = now
    cv.decision_reason = reason
    audit.record(
        db,
        actor=actor,
        action="ACTIVATE_FLAT_FALLBACK_CURRICULUM",
        entity_type="curriculum_version",
        entity_id=cv.id,
        after={"status": "ACTIVE", "origin": "FLAT_FALLBACK", "topics": len(units)},
        reason=reason,
    )
    db.commit()
    return cv


# ------------------------------------------------------------------- reads


@dataclass
class TopicView:
    version: TopicVersion
    unit: Unit | None
    source_chunk_ids: list[uuid.UUID]


@dataclass
class EdgeView:
    edge: TopicPrereq
    external_subject_code: str | None = None
    external_topic_name: str | None = None


@dataclass
class GraphView:
    version: CurriculumVersion
    subject: Subject
    units: list[Unit]
    topics: list[TopicView]
    edges: list[EdgeView]
    flags: list[GraphValidationFlag]
    mappings: list[TopicMapping]
    agent_run: AgentRun | None
    threshold: SimilarityThreshold | None
    embedding_config: EmbeddingConfig | None
    blockers: list[str]
    is_owner: bool
    banner: str | None


def build_graph_view(db: Session, teacher: User, curriculum_version_id: uuid.UUID) -> GraphView:
    cv = version_for_teacher(db, teacher, curriculum_version_id)
    subject = db.get(Subject, cv.subject_id)
    assert subject is not None
    units = list(db.scalars(select(Unit).where(Unit.subject_id == subject.id).order_by(Unit.order_index)))
    unit_by_id = {u.id: u for u in units}
    tvs = _topic_versions(db, cv.id)
    chunk_rows = db.execute(
        select(TopicSourceChunk.topic_version_id, TopicSourceChunk.content_chunk_id).where(
            TopicSourceChunk.topic_version_id.in_([t.id for t in tvs] or [uuid.uuid4()])
        )
    ).all()
    chunks_by_tv: dict[uuid.UUID, list[uuid.UUID]] = {}
    for tv_id, chunk_id in chunk_rows:
        chunks_by_tv.setdefault(tv_id, []).append(chunk_id)
    topics = sorted(
        (
            TopicView(tv, unit_by_id.get(tv.unit_id) if tv.unit_id else None, chunks_by_tv.get(tv.id, []))
            for tv in tvs
        ),
        key=lambda t: (t.unit.order_index if t.unit else 10_000, t.version.order_index),
    )
    own_topic_ids = {tv.topic_id for tv in tvs}
    edge_rows = list(
        db.scalars(
            select(TopicPrereq).where(TopicPrereq.curriculum_version_id == cv.id).order_by(TopicPrereq.id)
        )
    )
    edges: list[EdgeView] = []
    for e in edge_rows:
        view = EdgeView(e)
        if e.prereq_topic_id not in own_topic_ids and e.prereq_curriculum_version_id is not None:
            ext = db.execute(
                select(TopicVersion.name, Subject.code)
                .join(CurriculumVersion, CurriculumVersion.id == TopicVersion.curriculum_version_id)
                .join(Subject, Subject.id == CurriculumVersion.subject_id)
                .where(
                    TopicVersion.curriculum_version_id == e.prereq_curriculum_version_id,
                    TopicVersion.topic_id == e.prereq_topic_id,
                )
            ).first()
            if ext:
                view.external_topic_name, view.external_subject_code = ext[0], ext[1]
        edges.append(view)
    flags = list(
        db.scalars(
            select(GraphValidationFlag)
            .where(GraphValidationFlag.curriculum_version_id == cv.id)
            .order_by(GraphValidationFlag.kind, GraphValidationFlag.id)
        )
    )
    mappings = list(
        db.scalars(
            select(TopicMapping).where(TopicMapping.curriculum_version_id == cv.id).order_by(TopicMapping.id)
        )
    )
    run = db.get(AgentRun, cv.agent_run_id) if cv.agent_run_id else None
    threshold = (
        db.get(SimilarityThreshold, cv.similarity_threshold_id) if cv.similarity_threshold_id else None
    )
    config = db.get(EmbeddingConfig, cv.embedding_config_id) if cv.embedding_config_id else None
    blockers = approval_blockers(db, cv) if cv.status in (CurriculumStatus.DRAFT,) else []
    return GraphView(
        version=cv,
        subject=subject,
        units=units,
        topics=topics,
        edges=edges,
        flags=flags,
        mappings=mappings,
        agent_run=run,
        threshold=threshold,
        embedding_config=config,
        blockers=blockers,
        is_owner=is_owner(db, teacher.id, subject.id),
        banner=CYCLE_BANNER if any(e.edge.dropped for e in edges) else None,
    )


def list_versions(db: Session, teacher: User, subject_id: uuid.UUID) -> list[CurriculumVersion]:
    require_assigned(db, teacher, subject_id)
    return list(
        db.scalars(
            select(CurriculumVersion)
            .where(CurriculumVersion.subject_id == subject_id)
            .order_by(CurriculumVersion.version_no.desc())
        )
    )


def get_active_version(db: Session, teacher: User, subject_id: uuid.UUID) -> CurriculumVersion:
    require_assigned(db, teacher, subject_id)
    cv = db.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.subject_id == subject_id, CurriculumVersion.status == CurriculumStatus.ACTIVE
        )
    )
    if cv is None:
        raise NotFoundError("This Subject has no active curriculum yet.")
    return cv
