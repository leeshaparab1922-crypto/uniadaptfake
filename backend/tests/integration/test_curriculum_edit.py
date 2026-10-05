"""FR-CUR-003 Teacher graph editing on real PostgreSQL. Marker: pg. Fake LLM and embedder."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.audit_log import AuditLog
from app.models.curriculum import (
    CurriculumStatus,
    FlagKind,
    GraphValidationFlag,
    MappingKind,
    TopicMapping,
    TopicPrereq,
    TopicVersion,
    ValidationStatus,
)
from app.services import curriculum_edit_service as edits
from app.services import curriculum_service as cs
from tests.support.curriculum_helpers import (
    ScriptedEmbedder,
    add_active_curriculum,
    add_subject,
    generate,
    prepare,
)

pytestmark = pytest.mark.pg


@pytest.fixture()
def draft(pg_session):
    setup = prepare(pg_session)
    cv, _ = generate(pg_session, setup)
    ids = {tv.name: tv.topic_id for tv in pg_session.scalars(select(TopicVersion))}
    return setup, cv, ids


def _live_edges(db, cv):
    return list(
        db.scalars(
            select(TopicPrereq).where(
                TopicPrereq.curriculum_version_id == cv.id, TopicPrereq.dropped.is_(False)
            )
        )
    )


def _tv(db, cv, topic_id):
    return db.scalar(
        select(TopicVersion).where(
            TopicVersion.curriculum_version_id == cv.id, TopicVersion.topic_id == topic_id
        )
    )


EMB = ScriptedEmbedder


def test_rename_keeps_stable_id_and_records_mapping(pg_session, draft):
    setup, cv, ids = draft
    edits.update_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"name": "Array Basics"},
        embedder=EMB(),
    )
    tv = _tv(pg_session, cv, ids["Arrays"])
    assert tv.name == "Array Basics"
    mapping = pg_session.scalar(select(TopicMapping).where(TopicMapping.kind == MappingKind.RENAME))
    assert mapping.from_topic_id == mapping.to_topic_id == ids["Arrays"]


def test_every_edit_bumps_revision_and_reruns_validation(pg_session, draft):
    setup, cv, ids = draft
    emb = EMB()
    edits.update_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"est_hours": 5},
        embedder=emb,
    )
    pg_session.refresh(cv)
    assert cv.revision == 2 and cv.validated_revision == 2 and cv.validation_status == ValidationStatus.PASSED
    actions = [a.action for a in pg_session.scalars(select(AuditLog).where(AuditLog.entity_id == str(cv.id)))]
    assert "EDIT_CURRICULUM_TOPIC" in actions and actions.count("VALIDATE_CURRICULUM") == 2
    # renaming changes the embedding text, so exactly that Topic is re-embedded
    edits.update_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"name": "Arrays v2"},
        embedder=emb,
    )
    assert emb.calls == 1 and emb.texts[0].startswith("Arrays v2")


def test_approval_stays_pending_after_edit_owner_still_decides(pg_session, draft):
    setup, cv, ids = draft
    edits.update_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"name": "Arrays!"},
        embedder=EMB(),
    )
    pg_session.refresh(cv)
    assert cv.status == CurriculumStatus.DRAFT and cv.decided_by is None


def test_classify_each_enum(pg_session, draft):
    setup, cv, ids = draft
    for value in ("OPTIONAL", "SELF_STUDY", "CORE"):
        edits.update_topic(
            pg_session,
            actor=setup.world.co,
            curriculum_version_id=cv.id,
            topic_id=ids["Arrays"],
            changes={"classification": value},
            embedder=EMB(),
        )
        assert _tv(pg_session, cv, ids["Arrays"]).classification.value == value


def test_invalid_classification_400(pg_session, draft):
    setup, cv, ids = draft
    with pytest.raises(ValidationError):
        edits.update_topic(
            pg_session,
            actor=setup.world.co,
            curriculum_version_id=cv.id,
            topic_id=ids["Arrays"],
            changes={"classification": "MANDATORY"},
            embedder=EMB(),
        )
    with pytest.raises(ValidationError):
        edits.update_topic(
            pg_session,
            actor=setup.world.co,
            curriculum_version_id=cv.id,
            topic_id=ids["Arrays"],
            changes={},
            embedder=EMB(),
        )
    with pytest.raises(ValidationError):
        edits.update_topic(
            pg_session,
            actor=setup.world.co,
            curriculum_version_id=cv.id,
            topic_id=ids["Arrays"],
            changes={"surprise": 1},
            embedder=EMB(),
        )


def test_hours_must_be_positive(pg_session, draft):
    setup, cv, ids = draft
    for bad in (0, -1):
        with pytest.raises(ValidationError):
            edits.update_topic(
                pg_session,
                actor=setup.world.co,
                curriculum_version_id=cv.id,
                topic_id=ids["Arrays"],
                changes={"est_hours": bad},
                embedder=EMB(),
            )


def test_blank_name_and_empty_outcomes_rejected(pg_session, draft):
    setup, cv, ids = draft
    for changes in ({"name": "   "}, {"outcomes": []}, {"outcomes": ["ok", " "]}):
        with pytest.raises(ValidationError):
            edits.update_topic(
                pg_session,
                actor=setup.world.co,
                curriculum_version_id=cv.id,
                topic_id=ids["Arrays"],
                changes=changes,
                embedder=EMB(),
            )


def test_merge_maps_old_ids_to_target_and_remaps_edges(pg_session, draft):
    setup, cv, ids = draft
    edits.merge_topics(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_ids=[ids["Arrays"], ids["Linked Lists"]],
        target_topic_id=ids["Arrays"],
        name="Linear Structures",
        embedder=EMB(),
    )
    names = {
        tv.name: tv
        for tv in pg_session.scalars(select(TopicVersion).where(TopicVersion.curriculum_version_id == cv.id))
    }
    assert set(names) == {"Linear Structures", "Binary Trees"}
    assert names["Linear Structures"].topic_id == ids["Arrays"]
    assert names["Linear Structures"].est_hours == 6  # 3 + 3
    mapping = pg_session.scalar(select(TopicMapping).where(TopicMapping.kind == MappingKind.MERGE))
    assert mapping.from_topic_id == ids["Linked Lists"] and mapping.to_topic_id == ids["Arrays"]
    # the Binary Trees -> Linked Lists edge now points at the merged Topic; the A<->B edges vanished
    edges = list(pg_session.scalars(select(TopicPrereq).where(TopicPrereq.curriculum_version_id == cv.id)))
    assert [(e.topic_id, e.prereq_topic_id) for e in edges] == [(ids["Binary Trees"], ids["Arrays"])]


def test_merge_needs_two_topics_including_target(pg_session, draft):
    setup, cv, ids = draft
    with pytest.raises(ValidationError):
        edits.merge_topics(
            pg_session,
            actor=setup.world.co,
            curriculum_version_id=cv.id,
            topic_ids=[ids["Arrays"]],
            target_topic_id=ids["Arrays"],
            name=None,
            embedder=EMB(),
        )
    with pytest.raises(ValidationError):
        edits.merge_topics(
            pg_session,
            actor=setup.world.co,
            curriculum_version_id=cv.id,
            topic_ids=[ids["Arrays"], ids["Linked Lists"]],
            target_topic_id=ids["Binary Trees"],
            name=None,
            embedder=EMB(),
        )


def test_split_maps_to_parts_and_assigns_edges_explicitly(pg_session, draft):
    setup, cv, ids = draft
    edits.split_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Binary Trees"],
        parts=[
            edits.SplitPart(name="Tree Basics", prereq_topic_ids=[ids["Linked Lists"]]),
            edits.SplitPart(name="Tree Traversals", est_hours=2.5),
        ],
        embedder=EMB(),
    )
    rows = {
        tv.name: tv
        for tv in pg_session.scalars(select(TopicVersion).where(TopicVersion.curriculum_version_id == cv.id))
    }
    assert set(rows) == {"Arrays", "Linked Lists", "Tree Basics", "Tree Traversals"}
    mappings = list(pg_session.scalars(select(TopicMapping).where(TopicMapping.kind == MappingKind.SPLIT)))
    assert {m.from_topic_id for m in mappings} == {ids["Binary Trees"]}
    assert {m.to_topic_id for m in mappings} == {
        rows["Tree Basics"].topic_id,
        rows["Tree Traversals"].topic_id,
    }
    assert float(rows["Tree Traversals"].est_hours) == 2.5 and float(rows["Tree Basics"].est_hours) == 2.0
    live = {(e.topic_id, e.prereq_topic_id) for e in _live_edges(pg_session, cv)}
    assert (rows["Tree Basics"].topic_id, ids["Linked Lists"]) in live
    assert all(ids["Binary Trees"] not in pair for pair in live)
    with pytest.raises(ValidationError):
        edits.split_topic(
            pg_session,
            actor=setup.world.co,
            curriculum_version_id=cv.id,
            topic_id=ids["Arrays"],
            parts=[edits.SplitPart(name="only one")],
            embedder=EMB(),
        )


def test_reorder_within_unit_persists_order_index(pg_session, draft):
    setup, cv, ids = draft
    unit_id = _tv(pg_session, cv, ids["Arrays"]).unit_id
    edits.reorder_unit_topics(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        unit_id=unit_id,
        ordered_topic_ids=[ids["Linked Lists"], ids["Arrays"]],
        embedder=EMB(),
    )
    assert _tv(pg_session, cv, ids["Linked Lists"]).order_index == 1
    assert _tv(pg_session, cv, ids["Arrays"]).order_index == 2
    with pytest.raises(ValidationError):  # must list exactly the Unit's Topics
        edits.reorder_unit_topics(
            pg_session,
            actor=setup.world.co,
            curriculum_version_id=cv.id,
            unit_id=unit_id,
            ordered_topic_ids=[ids["Arrays"]],
            embedder=EMB(),
        )


def test_add_edge_creating_a_cycle_drops_lowest_confidence_and_flags(pg_session, draft):
    setup, cv, ids = draft
    # Arrays->Linked Lists (0.8) and Binary Trees->Linked Lists (0.9) exist; closing the loop:
    edits.add_edge(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Linked Lists"],
        prereq_topic_id=ids["Binary Trees"],
        confidence=0.3,
        prereq_curriculum_version_id=None,
        embedder=EMB(),
    )
    live = _live_edges(pg_session, cv)
    pairs = {(e.topic_id, e.prereq_topic_id) for e in live}
    assert (
        ids["Linked Lists"],
        ids["Binary Trees"],
    ) not in pairs  # the 0.3 edge was the weakest in the cycle
    flags = list(
        pg_session.scalars(
            select(GraphValidationFlag).where(GraphValidationFlag.kind == FlagKind.CYCLE_EDGE_DROPPED)
        )
    )
    assert len(flags) == 2  # the earlier 0.4 drop and the new one
    pg_session.refresh(cv)
    assert cv.validation_status == ValidationStatus.PASSED and cv.revision == 2


def test_add_edge_rules(pg_session, draft):
    setup, cv, ids = draft
    kw = dict(
        actor=setup.world.co, curriculum_version_id=cv.id, prereq_curriculum_version_id=None, embedder=EMB()
    )
    with pytest.raises(ValidationError):
        edits.add_edge(
            pg_session, topic_id=ids["Arrays"], prereq_topic_id=ids["Arrays"], confidence=1.0, **kw
        )
    with pytest.raises(ValidationError):
        edits.add_edge(
            pg_session, topic_id=ids["Arrays"], prereq_topic_id=ids["Binary Trees"], confidence=1.5, **kw
        )
    with pytest.raises(ConflictError):  # Arrays -> Linked Lists already exists
        edits.add_edge(
            pg_session, topic_id=ids["Arrays"], prereq_topic_id=ids["Linked Lists"], confidence=1.0, **kw
        )
    import uuid

    with pytest.raises(NotFoundError):
        edits.add_edge(pg_session, topic_id=ids["Arrays"], prereq_topic_id=uuid.uuid4(), confidence=1.0, **kw)


def test_add_cross_subject_edge_only_to_earlier_semester_pinned(pg_session, draft):
    setup, cv, ids = draft
    earlier = add_subject(pg_session, setup.world, semester_no=2, code="MA201")
    later = add_subject(pg_session, setup.world, semester_no=5, code="CS501")
    ext_cv, ext = add_active_curriculum(pg_session, earlier, setup.world.admin, ["Sets"])
    late_cv, late = add_active_curriculum(pg_session, later, setup.world.admin, ["Compilers"])
    base = dict(
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        confidence=0.7,
        embedder=EMB(),
    )
    with pytest.raises(ValidationError, match="earlier-semester"):
        edits.add_edge(
            pg_session, prereq_topic_id=late[0].id, prereq_curriculum_version_id=late_cv.id, **base
        )
    with pytest.raises(ValidationError, match="earlier-semester"):  # right topic, wrong pinned version
        edits.add_edge(pg_session, prereq_topic_id=ext[0].id, prereq_curriculum_version_id=late_cv.id, **base)
    edits.add_edge(pg_session, prereq_topic_id=ext[0].id, prereq_curriculum_version_id=ext_cv.id, **base)
    edge = pg_session.scalar(select(TopicPrereq).where(TopicPrereq.prereq_topic_id == ext[0].id))
    assert edge.prereq_curriculum_version_id == ext_cv.id and edge.source.value == "TEACHER"


def test_delete_edge_revalidates(pg_session, draft):
    setup, cv, ids = draft
    edge = _live_edges(pg_session, cv)[0]
    edits.delete_edge(
        pg_session, actor=setup.world.co, curriculum_version_id=cv.id, edge_id=edge.id, embedder=EMB()
    )
    assert pg_session.get(TopicPrereq, edge.id) is None
    pg_session.refresh(cv)
    assert cv.revision == 2 and cv.validated_revision == 2
    with pytest.raises(NotFoundError):
        edits.delete_edge(
            pg_session, actor=setup.world.co, curriculum_version_id=cv.id, edge_id=edge.id, embedder=EMB()
        )


def test_delete_topic_removes_incident_edges(pg_session, draft):
    setup, cv, ids = draft
    edits.delete_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Linked Lists"],
        embedder=EMB(),
    )
    assert _tv(pg_session, cv, ids["Linked Lists"]) is None
    assert all(
        ids["Linked Lists"] not in (e.topic_id, e.prereq_topic_id)
        for e in pg_session.scalars(select(TopicPrereq).where(TopicPrereq.curriculum_version_id == cv.id))
    )


def test_assign_unit_clears_orphan_flag(pg_session, draft):
    setup, cv, ids = draft
    tv = _tv(pg_session, cv, ids["Arrays"])
    unit_id = tv.unit_id
    tv.unit_id = None
    cv.revision += 1
    pg_session.commit()
    cs.validate_version(pg_session, cv.id, embedder=EMB())
    assert pg_session.scalar(select(GraphValidationFlag).where(GraphValidationFlag.kind == FlagKind.ORPHAN))
    edits.update_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"unit_id": unit_id},
        embedder=EMB(),
    )
    assert (
        pg_session.scalar(select(GraphValidationFlag).where(GraphValidationFlag.kind == FlagKind.ORPHAN))
        is None
    )
    pg_session.refresh(cv)
    assert cv.validation_status == ValidationStatus.PASSED
    other = add_subject(pg_session, setup.world, semester_no=1, code="X1")
    from app.models.subject import Unit

    foreign = pg_session.scalar(select(Unit).where(Unit.subject_id == other.id))
    with pytest.raises(ValidationError):  # a Unit of another Subject
        edits.update_topic(
            pg_session, actor=setup.world.co, curriculum_version_id=cv.id, topic_id=ids["Arrays"],
            changes={"unit_id": foreign.id}, embedder=EMB(),
        )


def test_co_teacher_can_edit_unassigned_cannot(pg_session, draft):
    setup, cv, ids = draft
    edits.update_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"est_hours": 4},
        embedder=EMB(),
    )
    edits.update_topic(
        pg_session,
        actor=setup.world.owner,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"est_hours": 5},
        embedder=EMB(),
    )
    with pytest.raises(NotFoundError):
        edits.update_topic(
            pg_session,
            actor=setup.world.outsider,
            curriculum_version_id=cv.id,
            topic_id=ids["Arrays"],
            changes={"est_hours": 6},
            embedder=EMB(),
        )
    assert float(_tv(pg_session, cv, ids["Arrays"]).est_hours) == 5.0


def test_edit_on_active_version_rejected_409(pg_session, draft):
    setup, cv, ids = draft
    cs.approve_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason=None)
    before = float(_tv(pg_session, cv, ids["Arrays"]).est_hours)
    with pytest.raises(ConflictError, match="immutable"):
        edits.update_topic(
            pg_session,
            actor=setup.world.owner,
            curriculum_version_id=cv.id,
            topic_id=ids["Arrays"],
            changes={"est_hours": 9},
            embedder=EMB(),
        )
    with pytest.raises(ConflictError):
        edits.delete_topic(
            pg_session,
            actor=setup.world.owner,
            curriculum_version_id=cv.id,
            topic_id=ids["Arrays"],
            embedder=EMB(),
        )
    assert float(_tv(pg_session, cv, ids["Arrays"]).est_hours) == before


def test_editing_a_returned_draft_reopens_it(pg_session, draft):
    setup, cv, ids = draft
    cs.reject_version(pg_session, actor=setup.world.owner, curriculum_version_id=cv.id, reason="fix names")
    edits.update_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"name": "Arrays (fixed)"},
        embedder=EMB(),
    )
    pg_session.refresh(cv)
    assert cv.status == CurriculumStatus.DRAFT and cv.validated_revision == cv.revision


def test_edit_audit_rows_carry_actor_before_after(pg_session, draft):
    setup, cv, ids = draft
    edits.update_topic(
        pg_session,
        actor=setup.world.co,
        curriculum_version_id=cv.id,
        topic_id=ids["Arrays"],
        changes={"est_hours": 7},
        embedder=EMB(),
    )
    row = pg_session.scalar(select(AuditLog).where(AuditLog.action == "EDIT_CURRICULUM_TOPIC"))
    assert row.actor_id == setup.world.co.id
    assert row.before["est_hours"] == "3.00" and row.after["est_hours"] == "7.00"
