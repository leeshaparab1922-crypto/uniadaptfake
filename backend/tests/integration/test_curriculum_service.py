"""FR-CUR-001, FR-CUR-002, FR-CUR-004; AC-006, AC-007; BUS-020..023, BUS-043, BUS-050 on real
PostgreSQL + pgvector. Marker: pg. The LLM and the embedder are fakes; no key, no network."""

from __future__ import annotations

import json
import threading
import uuid

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models.audit_log import AuditLog
from app.models.curriculum import (
    CurriculumStatus,
    CurriculumVersion,
    FlagKind,
    GraphValidationFlag,
    ThresholdStatus,
    Topic,
    TopicPrereq,
    TopicSourceChunk,
    TopicVersion,
    ValidationStatus,
)
from app.models.user import User
from app.schemas.curriculum_agent import CurriculumDraft
from app.services import curriculum_service as cs
from app.services import similarity_config_service as thresholds
from app.services.embedding_config_service import get_or_create_active_config
from tests.support.curriculum_helpers import (
    ScriptedEmbedder,
    add_active_curriculum,
    add_subject,
    generate,
    prepare,
)
from tests.support.fakes import RecordingQueue
from tests.support.llm import FakeLLMProvider, fixture_json, fixture_text
from tests.support.world import build_world

pytestmark = pytest.mark.pg


def _edges(db, cv):
    return list(db.scalars(select(TopicPrereq).where(TopicPrereq.curriculum_version_id == cv.id)))


def _tv_by_name(db, cv):
    return {
        tv.name: tv
        for tv in db.scalars(select(TopicVersion).where(TopicVersion.curriculum_version_id == cv.id))
    }


# ------------------------------------------------------------------ FR-CUR-001


def test_assigned_teacher_request_creates_generating_version_and_queues(pg_session):
    setup = prepare(pg_session)
    queue = RecordingQueue()
    cv = cs.request_generation(
        pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=queue
    )
    assert cv.status == CurriculumStatus.GENERATING and cv.version_no == 1
    assert cv.source_content_version_id == setup.syllabus.id
    assert queue.enqueued == [str(cv.id)]
    # a second request while one is in flight is refused
    with pytest.raises(ConflictError):
        cs.request_generation(
            pg_session, actor=setup.world.owner, subject_id=setup.world.subject.id, queue=queue
        )


def test_generate_without_active_syllabus_conflict(pg_session):
    world = build_world(pg_session)
    with pytest.raises(ConflictError, match="active, successfully ingested syllabus"):
        cs.request_generation(
            pg_session, actor=world.owner, subject_id=world.subject.id, queue=RecordingQueue()
        )


def test_unassigned_teacher_generate_404_and_logs_denial(pg_session, caplog):
    setup = prepare(pg_session)
    with caplog.at_level("WARNING"), pytest.raises(NotFoundError):
        cs.request_generation(
            pg_session, actor=setup.world.outsider, subject_id=setup.world.subject.id, queue=RecordingQueue()
        )
    assert any("access denied" in r.message for r in caplog.records)


def test_generation_persists_topics_edges_outcomes_with_stable_ids(pg_session):
    setup = prepare(pg_session)
    cv, outcome = generate(pg_session, setup)
    assert outcome.status == "DRAFT" and cv.status == CurriculumStatus.DRAFT
    topics = _tv_by_name(pg_session, cv)
    assert set(topics) == {"Arrays", "Linked Lists", "Binary Trees"}
    for tv in topics.values():
        assert tv.outcomes and tv.est_hours > 0 and pg_session.get(Topic, tv.topic_id) is not None
    assert len(_edges(pg_session, cv)) == 3
    assert cv.revision == 1 and cv.validated_revision == 1 and cv.validation_status == ValidationStatus.PASSED
    assert cv.agent_run_id == outcome.agent_run_id


def test_topic_weightage_derived_from_unit_not_stored(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    assert not hasattr(TopicVersion, "weightage") and not hasattr(TopicVersion, "exam_weightage")
    view = cs.build_graph_view(pg_session, setup.world.owner, cv.id)
    unit_weights = {u.id: u.weightage for u in view.units}
    arrays = next(t for t in view.topics if t.version.name == "Arrays")
    assert unit_weights[arrays.version.unit_id] == 34 and arrays.unit.weightage == 34


def test_sampled_topic_traces_to_version_file_locator(pg_session):
    setup = prepare(pg_session)
    data = fixture_json("cyclic")
    data["topics"][0]["source_chunk_ids"] = [str(setup.chunk_ids[0])]
    cv, _ = generate(pg_session, setup, llm=FakeLLMProvider(json.dumps(data)))
    row = pg_session.scalar(select(TopicSourceChunk))
    assert row is not None and row.content_chunk_id == setup.chunk_ids[0]
    from app.services import content_service

    chunk, version, _asset = content_service.resolve_chunk(pg_session, setup.world.co, row.content_chunk_id)
    assert version.id == setup.syllabus.id and chunk.locator and chunk.source_file


def test_active_version_unchanged_while_draft_generated(pg_session):
    setup = prepare(pg_session)
    first, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=first.id, reason="ok")
    second, _ = generate(pg_session, setup, fixture="tie")
    pg_session.refresh(first)
    assert first.status == CurriculumStatus.ACTIVE and second.status == CurriculumStatus.DRAFT
    assert cs.get_active_version(pg_session, setup.world.co, setup.world.subject.id).id == first.id


def test_refusal_marks_failed_no_graph(pg_session):
    from app.integrations.llm.base import LLMResponse

    setup = prepare(pg_session)
    refusal = LLMResponse("", "refusal", 5, 0)
    cv, outcome = generate(pg_session, setup, llm=FakeLLMProvider(refusal))
    assert outcome.status == "GENERATION_FAILED" and cv.status == CurriculumStatus.GENERATION_FAILED
    assert _tv_by_name(pg_session, cv) == {} and _edges(pg_session, cv) == []
    with pytest.raises(ConflictError):
        cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)


def test_schema_broken_output_fails_safely_with_no_topics(pg_session):
    setup = prepare(pg_session)
    llm = FakeLLMProvider(*[fixture_text("schema_broken")] * 3)
    cv, outcome = generate(pg_session, setup, llm=llm)
    assert cv.status == CurriculumStatus.GENERATION_FAILED and "schema" in cv.failure_message
    assert pg_session.scalar(select(func.count()).select_from(TopicVersion)) == 0


def test_outage_leaves_generating_and_nothing_partial_then_retry_succeeds(pg_session):
    from app.agents.curriculum_runner import run_generation
    from app.integrations.llm.base import LLMUnavailableError
    from tests.support.fakes import FakeEmbedder

    setup = prepare(pg_session)
    cv = cs.request_generation(
        pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=RecordingQueue()
    )
    outcome = run_generation(
        pg_session, cv.id, provider=FakeLLMProvider(LLMUnavailableError("down")), embedder=FakeEmbedder()
    )
    assert outcome.retry and outcome.status == "RETRY"
    pg_session.refresh(cv)
    assert cv.status == CurriculumStatus.GENERATING
    assert pg_session.scalar(select(func.count()).select_from(TopicVersion)) == 0
    again = run_generation(
        pg_session, cv.id, provider=FakeLLMProvider(fixture_text("cyclic")), embedder=FakeEmbedder()
    )
    assert again.status == "DRAFT"
    # idempotent: running it again is a no-op
    assert (
        run_generation(pg_session, cv.id, provider=FakeLLMProvider(), embedder=FakeEmbedder()).status
        == "SKIPPED"
    )


def test_prior_active_topic_id_is_kept_stable_when_agent_references_it(pg_session):
    setup = prepare(pg_session)
    first, _ = generate(pg_session, setup)
    prior_id = _tv_by_name(pg_session, first)["Arrays"].topic_id
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=first.id, reason=None)
    data = fixture_json("tie")
    data["topics"][0]["prior_topic_id"] = str(prior_id)
    second, _ = generate(pg_session, setup, llm=FakeLLMProvider(json.dumps(data)))
    assert _tv_by_name(pg_session, second)["Arrays"].topic_id == prior_id


# --------------------------------------------------------- cross-subject scope (A-6)


def _external_ref_json(topic_id, fixture="cyclic"):
    data = fixture_json(fixture)
    data["topics"][0]["prerequisites"].append({"prereq_ref": f"ext:{topic_id}", "confidence": 0.6})
    return json.dumps(data)


def test_cross_subject_edge_to_earlier_semester_pinned_to_exact_version(pg_session):
    setup = prepare(pg_session)
    earlier = add_subject(pg_session, setup.world, semester_no=2, code="MA201")
    ext_cv, ext_topics = add_active_curriculum(pg_session, earlier, setup.world.admin, ["Sets"])
    cv, outcome = generate(pg_session, setup, llm=FakeLLMProvider(_external_ref_json(ext_topics[0].id)))
    assert outcome.status == "DRAFT"
    cross = [e for e in _edges(pg_session, cv) if e.prereq_curriculum_version_id is not None]
    assert len(cross) == 1
    assert cross[0].prereq_topic_id == ext_topics[0].id and cross[0].prereq_curriculum_version_id == ext_cv.id
    view = cs.build_graph_view(pg_session, setup.world.owner, cv.id)
    ext = next(e for e in view.edges if e.edge.prereq_curriculum_version_id)
    assert ext.external_subject_code == "MA201" and ext.external_topic_name == "Sets"


def test_cross_subject_edge_to_same_or_later_semester_rejected(pg_session):
    setup = prepare(pg_session)
    same = add_subject(pg_session, setup.world, semester_no=3, code="CS302")
    later = add_subject(pg_session, setup.world, semester_no=4, code="CS401")
    for subject, code in ((same, "x"), (later, "y")):
        _cv, topics = add_active_curriculum(pg_session, subject, setup.world.admin, [f"T{code}"])
        view_subject = pg_session.get(type(setup.world.subject), setup.world.subject.id)
        offered = {r.topic_id for r in cs.offered_external_topics(pg_session, view_subject)}
        assert topics[0].id not in offered  # never offered to the agent
        # and if the model names it anyway, the agent's context check rejects the draft
        cv, outcome = generate(
            pg_session, setup, llm=FakeLLMProvider(*[_external_ref_json(topics[0].id)] * 3)
        )
        assert cv.status == CurriculumStatus.GENERATION_FAILED
    assert (
        pg_session.scalar(select(func.count()).select_from(TopicVersion).where(TopicVersion.name == "Arrays"))
        == 0
    )


def test_persist_skips_out_of_scope_edge_and_flags_it(pg_session):
    """Defence in depth: even if the agent check were bypassed, the service never stores it."""
    setup = prepare(pg_session)
    queue = RecordingQueue()
    cv = cs.request_generation(
        pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=queue
    )
    from tests.support.fakes import FakeEmbedder

    data = fixture_json("tie")
    data["topics"][0]["prerequisites"].append({"prereq_ref": f"ext:{uuid.uuid4()}", "confidence": 0.5})
    draft = CurriculumDraft.model_validate(data)
    from app.agents.curriculum_runner import run_generation  # noqa: F401 - import check only
    from app.models.ai import AgentRun, AgentRunStatus
    from app.prompts.registry import get_prompt
    from app.services.ai_config_service import ensure_active_config

    config = ensure_active_config(pg_session, "curriculum")
    _p, prompt_row = get_prompt(pg_session, "curriculum")
    run = AgentRun(
        agent="curriculum",
        provider_config_id=config.id,
        prompt_version_id=prompt_row.id,
        subject_id=cv.subject_id,
        requested_by=cv.created_by,
        status=AgentRunStatus.SUCCEEDED,
    )
    pg_session.add(run)
    pg_session.commit()
    cs.persist_draft(pg_session, cv.id, draft, agent_run_id=run.id)
    cs.validate_version(pg_session, cv.id, embedder=FakeEmbedder())
    flags = list(
        pg_session.scalars(
            select(GraphValidationFlag).where(GraphValidationFlag.kind == FlagKind.SCOPE_VIOLATION)
        )
    )
    assert len(flags) == 1 and not flags[0].blocking
    assert all(e.prereq_curriculum_version_id is None for e in _edges(pg_session, cv))


# ------------------------------------------------------------------ FR-CUR-002


def test_ac006_cyclic_draft_drops_lowest_confidence_edge_and_flags_it(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    topics = _tv_by_name(pg_session, cv)
    edges = _edges(pg_session, cv)
    dropped = [e for e in edges if e.dropped]
    assert len(dropped) == 1 and float(dropped[0].confidence) == 0.4
    assert dropped[0].topic_id == topics["Linked Lists"].topic_id
    kept = [e for e in edges if not e.dropped]
    assert {float(e.confidence) for e in kept} == {0.8, 0.9}
    flag = pg_session.scalar(
        select(GraphValidationFlag).where(GraphValidationFlag.kind == FlagKind.CYCLE_EDGE_DROPPED)
    )
    assert flag.edge_id == dropped[0].id and not flag.blocking
    assert "cycle" in flag.detail["banner"].lower()
    view = cs.build_graph_view(pg_session, setup.world.owner, cv.id)
    assert view.banner == "A prerequisite cycle was detected. Review the flagged relationship."


def test_tie_drops_ascending_normalized_pair_first(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup, fixture="tie")
    dropped = [e for e in _edges(pg_session, cv) if e.dropped]
    assert len(dropped) == 1
    assert (str(dropped[0].topic_id), str(dropped[0].prereq_topic_id)) == min(
        (str(e.topic_id), str(e.prereq_topic_id)) for e in _edges(pg_session, cv)
    )


def test_orphan_blocks_approval(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    tv = _tv_by_name(pg_session, cv)["Arrays"]
    tv.unit_id = None  # simulate a Topic left without a Unit
    cv.revision += 1
    pg_session.commit()
    cs.validate_version(pg_session, cv.id, embedder=ScriptedEmbedder())
    pg_session.refresh(cv)
    assert cv.validation_status == ValidationStatus.BLOCKED
    assert pg_session.scalar(
        select(GraphValidationFlag).where(GraphValidationFlag.kind == FlagKind.ORPHAN)
    ).blocking
    with pytest.raises(ConflictError, match="no Unit"):
        cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)


def test_validation_records_embedding_config_and_threshold_ids(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    config = get_or_create_active_config(pg_session)
    assert cv.embedding_config_id == config.id
    threshold = thresholds.resolve_threshold(pg_session, config)
    assert cv.similarity_threshold_id == threshold.id and threshold.status == ThresholdStatus.ACTIVE
    for tv in _tv_by_name(pg_session, cv).values():
        assert tv.embedding is not None and len(tv.embedding) == 1024 and tv.embedding_config_id == config.id


def test_unvalidated_threshold_blocks_activation(pg_session):
    setup = prepare(pg_session, threshold_active=False)
    cv, _ = generate(pg_session, setup)
    view = cs.build_graph_view(pg_session, setup.world.owner, cv.id)
    assert view.threshold.status == ThresholdStatus.DRAFT
    assert float(view.threshold.value) == float(settings.duplicate_threshold_default)
    with pytest.raises(ConflictError, match="threshold"):
        cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)
    # validating and activating the threshold lifts the block without regenerating
    row = view.threshold
    thresholds.record_validation(pg_session, row.id, report={"ok": 1}, passed=True)
    thresholds.activate_threshold(pg_session, row.id)
    cs.validate_version(pg_session, cv.id, embedder=ScriptedEmbedder())
    assert (
        cs.approve_version(
            pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None
        ).status
        == CurriculumStatus.ACTIVE
    )


def test_changed_embedding_model_requires_new_validated_threshold(pg_session, monkeypatch):
    from app.core.config import settings

    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    monkeypatch.setattr(settings, "embedding_model_revision", "f" * 40)  # a new model revision
    cs.validate_version(pg_session, cv.id, embedder=ScriptedEmbedder())
    pg_session.refresh(cv)
    assert (
        pg_session.get(type(get_or_create_active_config(pg_session)), cv.embedding_config_id).model_revision
        == "f" * 40
    )
    with pytest.raises(ConflictError, match="threshold"):
        cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)


def test_duplicates_flagged_visibly_but_do_not_block(pg_session):
    setup = prepare(pg_session)
    emb = ScriptedEmbedder(
        {
            "Arrays": ScriptedEmbedder.with_cosine(1.0),
            "Linked Lists": ScriptedEmbedder.with_cosine(0.95),
            "Binary Trees": [0.0, 0.0, 1.0] + [0.0] * 1021,
        }
    )
    cv, _ = generate(pg_session, setup, embedder=emb)
    flags = list(
        pg_session.scalars(
            select(GraphValidationFlag).where(GraphValidationFlag.kind == FlagKind.DUPLICATE_TOPIC)
        )
    )
    assert (
        len(flags) == 1
        and flags[0].detail["similarity"] > float(settings.duplicate_threshold_default)
        and flags[0].detail["threshold"] == settings.duplicate_threshold_default
    )
    assert not flags[0].blocking and cv.validation_status == ValidationStatus.PASSED


def test_validate_rejects_non_draft(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)
    with pytest.raises(ConflictError):
        cs.validate_version(pg_session, cv.id, embedder=ScriptedEmbedder())


# ------------------------------------------------------------------ FR-CUR-004


def test_ac007_owner_approves_valid_draft_becomes_active_prior_superseded_traceable(pg_session):
    setup = prepare(pg_session)
    first, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=first.id, reason="v1")
    second, _ = generate(pg_session, setup, fixture="tie")
    approved = cs.approve_version(
        pg_session, actor=setup.world.owner, curriculum_version_id=second.id, reason="v2"
    )
    pg_session.refresh(first)
    assert approved.status == CurriculumStatus.ACTIVE and approved.supersedes_version_id == first.id
    assert first.status == CurriculumStatus.SUPERSEDED
    assert approved.decided_by == setup.world.owner.id and approved.activated_at is not None
    # the superseded graph is still fully readable
    old = cs.build_graph_view(pg_session, setup.world.co, first.id)
    assert len(old.topics) == 3 and old.version.status == CurriculumStatus.SUPERSEDED


def test_co_teacher_approval_blocked_403(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    with pytest.raises(ForbiddenError):
        cs.approve_version(pg_session, actor=setup.world.co, curriculum_version_id=cv.id, reason=None)
    with pytest.raises(ForbiddenError):
        cs.reject_version(pg_session, actor=setup.world.co, curriculum_version_id=cv.id, reason=None)
    with pytest.raises(ForbiddenError):
        cs.activate_fallback(pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, reason=None)
    with pytest.raises(NotFoundError):
        cs.approve_version(pg_session, actor=setup.world.outsider, curriculum_version_id=cv.id, reason=None)
    pg_session.refresh(cv)
    assert cv.status == CurriculumStatus.DRAFT


def test_remaining_cycle_blocks_approval_ac006_negative(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup, fixture="tie")
    dropped = next(e for e in _edges(pg_session, cv) if e.dropped)
    dropped.dropped = False  # force a cycle back into the stored graph, validation still marked PASSED
    pg_session.commit()
    with pytest.raises(ConflictError, match="cycle remains"):
        cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)


def test_approve_blocked_when_validated_revision_is_stale(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    cv.revision += 1  # a change that has not been revalidated
    pg_session.commit()
    with pytest.raises(ConflictError, match="out of date"):
        cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)


def test_agent_failed_version_cannot_be_approved(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup, llm=FakeLLMProvider(*[fixture_text("schema_broken")] * 3))
    with pytest.raises(ConflictError, match="DRAFT"):
        cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)


def test_reject_returns_draft_prior_active_unchanged(pg_session):
    setup = prepare(pg_session)
    first, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=first.id, reason=None)
    second, _ = generate(pg_session, setup, fixture="tie")
    rejected = cs.reject_version(
        pg_session, actor=setup.world.owner, curriculum_version_id=second.id, reason="not good"
    )
    pg_session.refresh(first)
    assert rejected.status == CurriculumStatus.RETURNED and rejected.decision_reason == "not good"
    assert first.status == CurriculumStatus.ACTIVE
    with pytest.raises(ConflictError):
        cs.reject_version(pg_session, actor=setup.world.owner, curriculum_version_id=second.id, reason=None)


def test_fallback_only_when_no_active_and_owner(pg_session):
    setup = prepare(pg_session)
    cv = cs.activate_fallback(
        pg_session, actor=setup.world.owner, subject_id=setup.world.subject.id, reason="LLM down"
    )
    assert cv.status == CurriculumStatus.ACTIVE and cv.origin.value == "FLAT_FALLBACK"
    with pytest.raises(ConflictError, match="already has an active curriculum"):
        cs.activate_fallback(
            pg_session, actor=setup.world.owner, subject_id=setup.world.subject.id, reason=None
        )


def test_fallback_has_no_edges_and_unit_order(pg_session):
    setup = prepare(pg_session)
    cv = cs.activate_fallback(
        pg_session, actor=setup.world.owner, subject_id=setup.world.subject.id, reason=None
    )
    view = cs.build_graph_view(pg_session, setup.world.co, cv.id)
    assert [t.version.name for t in view.topics] == ["Basics", "Trees", "Graphs"]
    assert [t.unit.order_index for t in view.topics] == [1, 2, 3]
    assert view.edges == [] and cv.validation_status == ValidationStatus.PASSED


def test_fallback_after_rejected_draft_when_no_active_exists(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    cs.reject_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason="unusable")
    fallback = cs.activate_fallback(
        pg_session, actor=setup.world.owner, subject_id=setup.world.subject.id, reason="use units"
    )
    assert fallback.status == CurriculumStatus.ACTIVE and fallback.version_no == 2


def test_fallback_rejected_when_active_exists(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)
    with pytest.raises(ConflictError):
        cs.activate_fallback(
            pg_session, actor=setup.world.owner, subject_id=setup.world.subject.id, reason=None
        )


def test_decisions_write_audit_rows_same_txn(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason="why")
    actions = {
        a.action: a for a in pg_session.scalars(select(AuditLog).where(AuditLog.entity_id == str(cv.id)))
    }
    assert {
        "REQUEST_CURRICULUM_GENERATION",
        "CURRICULUM_DRAFT_CREATED",
        "VALIDATE_CURRICULUM",
        "APPROVE_CURRICULUM",
    } <= set(actions)
    assert (
        actions["APPROVE_CURRICULUM"].actor_id == setup.world.owner.id
        and actions["APPROVE_CURRICULUM"].reason == "why"
    )


def test_failure_mid_transition_leaves_prior_active(pg_session, monkeypatch):
    setup = prepare(pg_session)
    first, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=first.id, reason=None)
    second, _ = generate(pg_session, setup, fixture="tie")

    def boom(*a, **k):
        raise RuntimeError("audit failed")

    monkeypatch.setattr(cs.audit, "record", boom)
    with pytest.raises(RuntimeError):
        cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=second.id, reason=None)
    pg_session.rollback()
    pg_session.refresh(first)
    pg_session.refresh(second)
    assert first.status == CurriculumStatus.ACTIVE and second.status == CurriculumStatus.DRAFT


def test_get_active_returns_active_chain_and_prior_resolvable(pg_session):
    setup = prepare(pg_session)
    first, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=first.id, reason=None)
    second, _ = generate(pg_session, setup, fixture="tie")
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=second.id, reason=None)
    assert cs.get_active_version(pg_session, setup.world.co, setup.world.subject.id).id == second.id
    chain = cs.list_versions(pg_session, setup.world.co, setup.world.subject.id)
    assert [v.status for v in chain] == [CurriculumStatus.ACTIVE, CurriculumStatus.SUPERSEDED]
    assert len(cs.build_graph_view(pg_session, setup.world.co, first.id).topics) == 3
    with pytest.raises(NotFoundError):
        cs.get_active_version(
            pg_session, setup.world.co, add_subject(pg_session, setup.world, semester_no=1, code="X101").id
        )


def test_concurrent_approvals_single_active(pg_committed):
    """Two Owner approvals of two DRAFTs race; the Subject lock serialises them and the partial
    unique index guarantees exactly one ACTIVE version."""
    factory = pg_committed
    with factory() as setup_db:
        setup = prepare(setup_db)
        a, _ = generate(setup_db, setup)
        owner_id, subject_id, a_id = setup.world.owner.id, setup.world.subject.id, a.id
        # a second DRAFT requires the first to be non-GENERATING, which it now is
        b, _ = generate(setup_db, setup, fixture="tie")
        b_id = b.id
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker(version_id):
        with factory() as db:
            actor = db.get(User, owner_id)
            barrier.wait()
            try:
                cs.approve_version(db, actor=actor, curriculum_version_id=version_id, reason=None)
                outcomes.append("ok")
            except Exception as exc:  # noqa: BLE001
                outcomes.append(type(exc).__name__)

    threads = [threading.Thread(target=worker, args=(v,)) for v in (a_id, b_id)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    with factory() as check:
        active = check.scalar(
            select(func.count())
            .select_from(CurriculumVersion)
            .where(
                CurriculumVersion.subject_id == subject_id,
                CurriculumVersion.status == CurriculumStatus.ACTIVE,
            )
        )
        superseded = check.scalar(
            select(func.count())
            .select_from(CurriculumVersion)
            .where(CurriculumVersion.status == CurriculumStatus.SUPERSEDED)
        )
    assert active == 1 and outcomes.count("ok") == 2 and superseded == 1


# ------------------------------------------------------------------ finding D1: never stuck GENERATING


def test_queue_failure_marks_the_new_version_failed_so_it_can_be_requested_again(pg_session):
    setup = prepare(pg_session)
    cv = cs.request_generation(
        pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=RecordingQueue(fail=True)
    )
    assert cv.status == CurriculumStatus.GENERATION_FAILED
    assert cv.failure_message == cs.QUEUE_FAILED_MESSAGE
    again = cs.request_generation(
        pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=RecordingQueue()
    )
    assert again.status == CurriculumStatus.GENERATING and again.version_no == cv.version_no + 1


def test_a_live_generation_blocks_a_new_request_and_says_when_it_is_stale(pg_session):
    setup = prepare(pg_session)
    queue = RecordingQueue()
    cs.request_generation(pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=queue)
    with pytest.raises(ConflictError, match="after"):
        cs.request_generation(
            pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=queue
        )


def test_a_stale_generation_is_marked_failed_and_a_new_one_starts(pg_session):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    setup = prepare(pg_session)
    queue = RecordingQueue()
    stuck = cs.request_generation(
        pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=queue
    )
    old = datetime.now(UTC) - timedelta(seconds=settings.effective_curriculum_stale_after_seconds + 60)
    pg_session.execute(
        update(CurriculumVersion)
        .where(CurriculumVersion.id == stuck.id)
        .values(created_at=old, updated_at=old)
        .execution_options(synchronize_session=False)
    )
    pg_session.commit()

    fresh = cs.request_generation(
        pg_session, actor=setup.world.owner, subject_id=setup.world.subject.id, queue=queue
    )
    pg_session.refresh(stuck)
    assert stuck.status == CurriculumStatus.GENERATION_FAILED
    assert stuck.failure_message == cs.STALE_GENERATION_MESSAGE
    assert fresh.status == CurriculumStatus.GENERATING and fresh.id != stuck.id
    assert queue.enqueued == [str(stuck.id), str(fresh.id)]


def test_mark_generation_failed_closes_running_agent_runs(pg_session):
    from app.models.ai import AgentRun, AgentRunStatus, PromptVersion
    from app.services.ai_config_service import ensure_active_config

    setup = prepare(pg_session)
    cv = cs.request_generation(
        pg_session, actor=setup.world.co, subject_id=setup.world.subject.id, queue=RecordingQueue()
    )
    run = AgentRun(  # what a worker leaves behind when it dies mid-call
        agent="curriculum",
        provider_config_id=ensure_active_config(pg_session, "curriculum").id,
        prompt_version_id=pg_session.scalar(
            select(PromptVersion.id).where(PromptVersion.agent == "curriculum").limit(1)
        ),
        subject_id=setup.world.subject.id,
        requested_by=setup.world.co.id,
        curriculum_version_id=cv.id,
        status=AgentRunStatus.RUNNING,
    )
    pg_session.add(run)
    pg_session.commit()

    cs.mark_generation_failed(pg_session, cv.id, "worker died")
    pg_session.refresh(run)
    pg_session.refresh(cv)
    assert cv.status == CurriculumStatus.GENERATION_FAILED
    assert run.status == AgentRunStatus.FAILED and run.error == "worker died" and run.finished_at is not None
