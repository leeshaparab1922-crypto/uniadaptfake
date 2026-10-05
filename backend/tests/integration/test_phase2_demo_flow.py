"""Section 43 Phase 2 demo with a stub LLM: cyclic syllabus -> 0.4 edge dropped -> CO edits but gets
403 on approve -> Owner activates the corrected graph -> the prior chain stays resolvable.
Marker: pg (the ACTIVE syllabus is inserted directly; the 2A upload/ingest path has its own tests)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.errors import ForbiddenError
from app.models.curriculum import CurriculumStatus, TopicPrereq
from app.services import content_service
from app.services import curriculum_edit_service as edits
from app.services import curriculum_service as cs
from tests.support.curriculum_helpers import generate, prepare
from tests.support.fakes import FakeEmbedder
from tests.support.llm import FakeLLMProvider, fixture_text
from tests.support.world import login

pytestmark = pytest.mark.pg


def test_section43_demo_cyclic_syllabus_co_edits_owner_activates(pg_client, pg_session):
    setup = prepare(pg_session)
    w = setup.world
    cv, _ = generate(pg_session, setup)  # the stub returns A->B 0.8 and B->A 0.4
    dropped = [e for e in pg_session.scalars(select(TopicPrereq)) if e.dropped]
    assert [float(e.confidence) for e in dropped] == [0.4]

    topic_id = cs.build_graph_view(pg_session, w.co, cv.id).topics[0].version.topic_id
    edits.update_topic(
        pg_session,
        actor=w.co,
        curriculum_version_id=cv.id,
        topic_id=topic_id,
        changes={"name": "Arrays (reviewed)"},
        embedder=FakeEmbedder(),
    )
    with pytest.raises(ForbiddenError):
        cs.approve_version(pg_session, actor=w.co, curriculum_version_id=cv.id, reason=None)
    headers = login(pg_client, w.co)
    resp = pg_client.post(f"/teacher/curriculum/versions/{cv.id}/approve", json={}, headers=headers)
    assert resp.status_code == 403

    active = cs.approve_version(pg_session, actor=w.owner, curriculum_version_id=cv.id, reason="corrected")
    assert active.status == CurriculumStatus.ACTIVE and active.revision == 2


def test_demo_second_activation_supersedes_prior_chain_resolvable(pg_client, pg_session):
    setup = prepare(pg_session)
    w = setup.world
    first, _ = generate(pg_session, setup)
    cs.approve_version(pg_session, actor=w.owner, curriculum_version_id=first.id, reason=None)
    second, _ = generate(pg_session, setup, llm=FakeLLMProvider(fixture_text("tie")))
    cs.approve_version(pg_session, actor=w.owner, curriculum_version_id=second.id, reason=None)
    headers = login(pg_client, w.co)
    body = pg_client.get(f"/teacher/curriculum/versions/{first.id}", headers=headers).json()
    assert body["version"]["status"] == "SUPERSEDED" and len(body["topics"]) == 3
    # citations of the superseded chain still resolve (C7 / NFR-DAT-002)
    chunk, version, _asset = content_service.resolve_chunk(pg_session, w.co, setup.chunk_ids[0])
    assert version.id == setup.syllabus.id and chunk.id == setup.chunk_ids[0]
