"""Teacher curriculum endpoints G1..G15. FR-CUR-001..004.

Role gate is TEACHER; *assignment* and *Subject Owner* checks happen in the service layer at
query level (NFR-SEC-006/007). Approve / reject / fallback are Owner-only (BUS-043). An
approved (ACTIVE) curriculum has no edit route that works: the services answer 409.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.core.config import settings
from app.core.deps import (
    CurrentUser,
    CurriculumQueueDep,
    DbSession,
    EmbedderDep,
    RateLimiterDep,
    csrf_protect,
    require_role,
)
from app.core.errors import RateLimitedError
from app.models.user import UserRole
from app.schemas.curriculum import (
    AgentRunOut,
    CurriculumGraphOut,
    CurriculumVersionOut,
    DecisionRequest,
    EdgeCreate,
    EdgeOut,
    EmbeddingConfigOut,
    FlagOut,
    MappingOut,
    MergeRequest,
    ReorderRequest,
    SplitRequest,
    ThresholdOut,
    TopicOut,
    TopicPatch,
    UnitOut,
    ValidationOut,
)
from app.services import curriculum_edit_service as edits
from app.services import curriculum_service as cs

router = APIRouter(
    prefix="/teacher",
    tags=["teacher-curriculum"],
    dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.TEACHER))],
)


def _graph_out(view: cs.GraphView) -> CurriculumGraphOut:
    unit_weight = {u.id: u.weightage for u in view.units}
    own = {t.version.topic_id for t in view.topics}
    return CurriculumGraphOut(
        version=CurriculumVersionOut.model_validate(view.version),
        units=[UnitOut.model_validate(u) for u in view.units],
        topics=[
            TopicOut(
                topic_id=t.version.topic_id,
                name=t.version.name,
                unit_id=t.version.unit_id,
                unit_weightage=unit_weight.get(t.version.unit_id) if t.version.unit_id else None,
                outcomes=list(t.version.outcomes),
                bloom_level=t.version.bloom_level,
                est_hours=float(t.version.est_hours),
                classification=t.version.classification,
                order_index=t.version.order_index,
                source_chunk_ids=t.source_chunk_ids,
                is_orphan=t.version.unit_id is None,
            )
            for t in view.topics
        ],
        edges=[
            EdgeOut(
                id=e.edge.id,
                topic_id=e.edge.topic_id,
                prereq_topic_id=e.edge.prereq_topic_id,
                confidence=float(e.edge.confidence),
                source=e.edge.source,
                approved_by_teacher=e.edge.approved_by_teacher,
                dropped=e.edge.dropped,
                drop_reason=e.edge.drop_reason,
                cross_subject=e.edge.prereq_topic_id not in own,
                prereq_curriculum_version_id=e.edge.prereq_curriculum_version_id,
                external_subject_code=e.external_subject_code,
                external_topic_name=e.external_topic_name,
            )
            for e in view.edges
        ],
        flags=[FlagOut.model_validate(f) for f in view.flags],
        mappings=[MappingOut.model_validate(m) for m in view.mappings],
        agent_run=AgentRunOut.model_validate(view.agent_run) if view.agent_run else None,
        threshold=ThresholdOut.model_validate(view.threshold) if view.threshold else None,
        embedding_config=(
            EmbeddingConfigOut.model_validate(view.embedding_config) if view.embedding_config else None
        ),
        approval_blockers=view.blockers,
        can_approve=view.is_owner and not view.blockers and view.version.status.value == "DRAFT",
        is_owner=view.is_owner,
        banner=view.banner,
    )


def _graph(db, user, cid: uuid.UUID) -> CurriculumGraphOut:
    return _graph_out(cs.build_graph_view(db, user, cid))


# G1
@router.post(
    "/subjects/{subject_id}/curriculum/generate",
    response_model=CurriculumVersionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_curriculum(
    subject_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    queue: CurriculumQueueDep,
    limiter: RateLimiterDep,
) -> CurriculumVersionOut:
    if not limiter.hit(
        f"generate:{current_user.id}",
        limit=settings.rate_limit_generate_per_teacher_per_window,
        window_seconds=settings.rate_limit_window_seconds,
    ):
        raise RateLimitedError("Too many generation requests. Please try again later.")
    cv = cs.request_generation(db, actor=current_user, subject_id=subject_id, queue=queue)
    return CurriculumVersionOut.model_validate(cv)


# G2
@router.get("/subjects/{subject_id}/curriculum/versions", response_model=list[CurriculumVersionOut])
def list_versions(
    subject_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> list[CurriculumVersionOut]:
    return [CurriculumVersionOut.model_validate(v) for v in cs.list_versions(db, current_user, subject_id)]


# G3
@router.get("/subjects/{subject_id}/curriculum/active", response_model=CurriculumGraphOut)
def get_active(subject_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> CurriculumGraphOut:
    cv = cs.get_active_version(db, current_user, subject_id)
    return _graph(db, current_user, cv.id)


# G4
@router.get("/curriculum/versions/{cid}", response_model=CurriculumGraphOut)
def get_graph(cid: uuid.UUID, db: DbSession, current_user: CurrentUser) -> CurriculumGraphOut:
    return _graph(db, current_user, cid)


# G5
@router.post("/curriculum/versions/{cid}/validate", response_model=ValidationOut)
def validate(
    cid: uuid.UUID, db: DbSession, current_user: CurrentUser, embedder: EmbedderDep
) -> ValidationOut:
    summary = cs.rerun_validation(db, actor=current_user, curriculum_version_id=cid, embedder=embedder)
    return ValidationOut(**summary.__dict__)


# G6
@router.patch("/curriculum/versions/{cid}/topics/{topic_id}", response_model=CurriculumGraphOut)
def patch_topic(
    cid: uuid.UUID,
    topic_id: uuid.UUID,
    body: TopicPatch,
    db: DbSession,
    current_user: CurrentUser,
    embedder: EmbedderDep,
) -> CurriculumGraphOut:
    edits.update_topic(
        db,
        actor=current_user,
        curriculum_version_id=cid,
        topic_id=topic_id,
        changes=body.model_dump(exclude_unset=True),
        embedder=embedder,
    )
    return _graph(db, current_user, cid)


# G7
@router.post("/curriculum/versions/{cid}/topics/merge", response_model=CurriculumGraphOut)
def merge_topics(
    cid: uuid.UUID, body: MergeRequest, db: DbSession, current_user: CurrentUser, embedder: EmbedderDep
) -> CurriculumGraphOut:
    edits.merge_topics(
        db,
        actor=current_user,
        curriculum_version_id=cid,
        topic_ids=body.topic_ids,
        target_topic_id=body.target_topic_id,
        name=body.name,
        embedder=embedder,
    )
    return _graph(db, current_user, cid)


# G8
@router.post("/curriculum/versions/{cid}/topics/{topic_id}/split", response_model=CurriculumGraphOut)
def split_topic(
    cid: uuid.UUID,
    topic_id: uuid.UUID,
    body: SplitRequest,
    db: DbSession,
    current_user: CurrentUser,
    embedder: EmbedderDep,
) -> CurriculumGraphOut:
    edits.split_topic(
        db,
        actor=current_user,
        curriculum_version_id=cid,
        topic_id=topic_id,
        parts=[edits.SplitPart(**p.model_dump()) for p in body.parts],
        embedder=embedder,
    )
    return _graph(db, current_user, cid)


# G9
@router.put("/curriculum/versions/{cid}/units/{unit_id}/topic-order", response_model=CurriculumGraphOut)
def reorder(
    cid: uuid.UUID,
    unit_id: uuid.UUID,
    body: ReorderRequest,
    db: DbSession,
    current_user: CurrentUser,
    embedder: EmbedderDep,
) -> CurriculumGraphOut:
    edits.reorder_unit_topics(
        db,
        actor=current_user,
        curriculum_version_id=cid,
        unit_id=unit_id,
        ordered_topic_ids=body.topic_ids,
        embedder=embedder,
    )
    return _graph(db, current_user, cid)


# G10
@router.post("/curriculum/versions/{cid}/edges", response_model=CurriculumGraphOut, status_code=201)
def add_edge(
    cid: uuid.UUID, body: EdgeCreate, db: DbSession, current_user: CurrentUser, embedder: EmbedderDep
) -> CurriculumGraphOut:
    edits.add_edge(
        db,
        actor=current_user,
        curriculum_version_id=cid,
        topic_id=body.topic_id,
        prereq_topic_id=body.prereq_topic_id,
        confidence=body.confidence,
        prereq_curriculum_version_id=body.prereq_curriculum_version_id,
        embedder=embedder,
    )
    return _graph(db, current_user, cid)


# G11
@router.delete("/curriculum/versions/{cid}/edges/{edge_id}", response_model=CurriculumGraphOut)
def delete_edge(
    cid: uuid.UUID, edge_id: uuid.UUID, db: DbSession, current_user: CurrentUser, embedder: EmbedderDep
) -> CurriculumGraphOut:
    edits.delete_edge(db, actor=current_user, curriculum_version_id=cid, edge_id=edge_id, embedder=embedder)
    return _graph(db, current_user, cid)


# G12
@router.delete("/curriculum/versions/{cid}/topics/{topic_id}", response_model=CurriculumGraphOut)
def delete_topic(
    cid: uuid.UUID, topic_id: uuid.UUID, db: DbSession, current_user: CurrentUser, embedder: EmbedderDep
) -> CurriculumGraphOut:
    edits.delete_topic(
        db, actor=current_user, curriculum_version_id=cid, topic_id=topic_id, embedder=embedder
    )
    return _graph(db, current_user, cid)


# G13
@router.post("/curriculum/versions/{cid}/approve", response_model=CurriculumVersionOut)
def approve(
    cid: uuid.UUID, body: DecisionRequest, db: DbSession, current_user: CurrentUser
) -> CurriculumVersionOut:
    cv = cs.approve_version(db, actor=current_user, curriculum_version_id=cid, reason=body.reason)
    return CurriculumVersionOut.model_validate(cv)


# G14
@router.post("/curriculum/versions/{cid}/reject", response_model=CurriculumVersionOut)
def reject(
    cid: uuid.UUID, body: DecisionRequest, db: DbSession, current_user: CurrentUser
) -> CurriculumVersionOut:
    cv = cs.reject_version(db, actor=current_user, curriculum_version_id=cid, reason=body.reason)
    return CurriculumVersionOut.model_validate(cv)


# G15
@router.post("/subjects/{subject_id}/curriculum/fallback", response_model=CurriculumVersionOut)
def fallback(
    subject_id: uuid.UUID, body: DecisionRequest, db: DbSession, current_user: CurrentUser
) -> CurriculumVersionOut:
    cv = cs.activate_fallback(db, actor=current_user, subject_id=subject_id, reason=body.reason)
    return CurriculumVersionOut.model_validate(cv)

