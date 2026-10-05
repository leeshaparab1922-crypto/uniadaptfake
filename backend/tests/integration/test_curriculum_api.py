"""Teacher curriculum endpoints G1..G15 over HTTP on real PostgreSQL. Marker: pg.
The API runs with a recording queue and a fake embedder; generation is driven with a fake LLM."""

from __future__ import annotations

import pytest

from app.agents.curriculum_runner import run_generation
from app.core.config import settings
from app.models.curriculum import CurriculumStatus, CurriculumVersion
from app.models.user import UserRole
from tests.support.curriculum_helpers import prepare
from tests.support.fakes import FakeEmbedder
from tests.support.llm import FakeLLMProvider, fixture_text
from tests.support.world import _user, login

pytestmark = pytest.mark.pg


@pytest.fixture()
def env(pg_session):
    return prepare(pg_session)


def _gen_via_api(client, headers, setup, db, fixture="cyclic"):
    resp = client.post(f"/teacher/subjects/{setup.world.subject.id}/curriculum/generate", headers=headers)
    assert resp.status_code == 202, resp.text
    cid = resp.json()["id"]
    import uuid

    run_generation(
        db, uuid.UUID(cid), provider=FakeLLMProvider(fixture_text(fixture)), embedder=FakeEmbedder()
    )
    return cid


# ------------------------------------------------------------------ G1


def test_assigned_teacher_generate_returns_202_generating(
    pg_client, pg_session, env, curriculum_queue_recorder
):
    headers = login(pg_client, env.world.co)
    resp = pg_client.post(f"/teacher/subjects/{env.world.subject.id}/curriculum/generate", headers=headers)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "GENERATING" and body["version_no"] == 1 and body["origin"] == "AGENT"
    assert curriculum_queue_recorder.enqueued == [body["id"]]


def test_generate_without_active_syllabus_409(pg_client, pg_session):
    from tests.support.world import build_world

    world = build_world(pg_session)
    headers = login(pg_client, world.owner)
    resp = pg_client.post(f"/teacher/subjects/{world.subject.id}/curriculum/generate", headers=headers)
    assert resp.status_code == 409 and "syllabus" in resp.json()["detail"]


def test_unassigned_teacher_generate_404(pg_client, pg_session, env):
    headers = login(pg_client, env.world.outsider)
    resp = pg_client.post(f"/teacher/subjects/{env.world.subject.id}/curriculum/generate", headers=headers)
    assert resp.status_code == 404
    assert pg_client.get(f"/teacher/subjects/{env.world.subject.id}/curriculum/versions").status_code == 404


def test_generate_is_rate_limited(pg_client, pg_session, env, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_generate_per_teacher_per_window", 1)
    headers = login(pg_client, env.world.co)
    url = f"/teacher/subjects/{env.world.subject.id}/curriculum/generate"
    assert pg_client.post(url, headers=headers).status_code == 202
    assert pg_client.post(url, headers=headers).status_code == 429


@pytest.mark.parametrize("role", [UserRole.STUDENT, UserRole.ADMIN])
def test_non_teacher_roles_forbidden(pg_client, pg_session, env, role):
    user = _user(pg_session, f"{role.value.lower()}-x@example.com", role)
    pg_session.commit()
    headers = login(pg_client, user)
    sid = env.world.subject.id
    assert pg_client.get(f"/teacher/subjects/{sid}/curriculum/versions").status_code == 403
    assert pg_client.post(f"/teacher/subjects/{sid}/curriculum/generate", headers=headers).status_code == 403


def test_unauthenticated_and_missing_csrf_rejected(pg_client, pg_session, env):
    sid = env.world.subject.id
    assert pg_client.get(f"/teacher/subjects/{sid}/curriculum/versions").status_code == 401
    login(pg_client, env.world.co)
    assert pg_client.post(f"/teacher/subjects/{sid}/curriculum/generate").status_code == 403  # no CSRF header


# ------------------------------------------------------------------ reads


def test_dropped_edge_flag_visible_in_graph_response(pg_client, pg_session, env):
    headers = login(pg_client, env.world.co)
    cid = _gen_via_api(pg_client, headers, env, pg_session)
    graph = pg_client.get(f"/teacher/curriculum/versions/{cid}").json()
    assert graph["version"]["status"] == "DRAFT" and graph["version"]["validation_status"] == "PASSED"
    assert graph["banner"] == "A prerequisite cycle was detected. Review the flagged relationship."
    dropped = [e for e in graph["edges"] if e["dropped"]]
    assert len(dropped) == 1 and dropped[0]["confidence"] == 0.4 and "cycle" in dropped[0]["drop_reason"]
    assert [f["kind"] for f in graph["flags"]] == ["CYCLE_EDGE_DROPPED"]
    assert graph["agent_run"]["status"] == "SUCCEEDED" and graph["agent_run"]["attempts"] == 1
    assert graph["threshold"]["status"] == "ACTIVE" and graph["embedding_config"]["model_id"] == "BAAI/bge-m3"
    weights = {t["name"]: t["unit_weightage"] for t in graph["topics"]}
    assert weights == {"Arrays": 34, "Linked Lists": 34, "Binary Trees": 33}


def test_validation_runs_before_review_and_graph_acyclic_unit_linked(pg_client, pg_session, env):
    headers = login(pg_client, env.world.co)
    cid = _gen_via_api(pg_client, headers, env, pg_session)
    graph = pg_client.get(f"/teacher/curriculum/versions/{cid}").json()
    assert all(t["unit_id"] and not t["is_orphan"] for t in graph["topics"])
    live = [e for e in graph["edges"] if not e["dropped"]]
    assert {(e["topic_id"], e["prereq_topic_id"]) for e in live}  # edges survive
    resp = pg_client.post(f"/teacher/curriculum/versions/{cid}/validate", headers=headers)
    assert resp.status_code == 200 and resp.json()["passed"] is True and resp.json()["dropped_edges"] == 1


def test_can_approve_only_for_owner_and_unblocked(pg_client, pg_session, env):
    co_headers = login(pg_client, env.world.co)
    cid = _gen_via_api(pg_client, co_headers, env, pg_session)
    assert pg_client.get(f"/teacher/curriculum/versions/{cid}").json()["can_approve"] is False  # CO
    login(pg_client, env.world.owner)
    body = pg_client.get(f"/teacher/curriculum/versions/{cid}").json()
    assert body["can_approve"] is True and body["is_owner"] is True and body["approval_blockers"] == []


def test_get_active_returns_active_chain_and_prior_resolvable(pg_client, pg_session, env):
    owner_headers = login(pg_client, env.world.owner)
    sid = env.world.subject.id
    assert pg_client.get(f"/teacher/subjects/{sid}/curriculum/active").status_code == 404
    first = _gen_via_api(pg_client, owner_headers, env, pg_session)
    assert (
        pg_client.post(
            f"/teacher/curriculum/versions/{first}/approve", json={"reason": "v1"}, headers=owner_headers
        ).status_code
        == 200
    )
    second = _gen_via_api(pg_client, owner_headers, env, pg_session, fixture="tie")
    assert (
        pg_client.post(
            f"/teacher/curriculum/versions/{second}/approve", json={}, headers=owner_headers
        ).status_code
        == 200
    )
    assert pg_client.get(f"/teacher/subjects/{sid}/curriculum/active").json()["version"]["id"] == second
    versions = pg_client.get(f"/teacher/subjects/{sid}/curriculum/versions").json()
    assert [v["status"] for v in versions] == ["ACTIVE", "SUPERSEDED"]
    assert pg_client.get(f"/teacher/curriculum/versions/{first}").json()["version"]["status"] == "SUPERSEDED"


# ------------------------------------------------------------------ edits (G5..G12)


def test_edit_endpoints_round_trip(pg_client, pg_session, env):
    headers = login(pg_client, env.world.co)
    cid = _gen_via_api(pg_client, headers, env, pg_session)
    graph = pg_client.get(f"/teacher/curriculum/versions/{cid}").json()
    t = {x["name"]: x for x in graph["topics"]}
    base = f"/teacher/curriculum/versions/{cid}"

    r = pg_client.patch(
        f"{base}/topics/{t['Arrays']['topic_id']}",
        json={"name": "Array Basics", "classification": "OPTIONAL"},
        headers=headers,
    )
    assert r.status_code == 200 and r.json()["version"]["revision"] == 2
    assert {x["name"] for x in r.json()["topics"]} == {"Array Basics", "Linked Lists", "Binary Trees"}

    r = pg_client.post(
        f"{base}/edges",
        json={
            "topic_id": t["Binary Trees"]["topic_id"],
            "prereq_topic_id": t["Arrays"]["topic_id"],
            "confidence": 0.6,
        },
        headers=headers,
    )
    assert r.status_code == 201 and r.json()["version"]["revision"] == 3
    edge_id = next(e["id"] for e in r.json()["edges"] if e["source"] == "TEACHER")
    assert pg_client.delete(f"{base}/edges/{edge_id}", headers=headers).json()["version"]["revision"] == 4

    unit = t["Arrays"]["unit_id"]
    r = pg_client.put(
        f"{base}/units/{unit}/topic-order",
        json={"topic_ids": [t["Linked Lists"]["topic_id"], t["Arrays"]["topic_id"]]},
        headers=headers,
    )
    assert r.status_code == 200 and [x["name"] for x in r.json()["topics"] if x["unit_id"] == unit] == [
        "Linked Lists",
        "Array Basics",
    ]

    r = pg_client.post(
        f"{base}/topics/{t['Binary Trees']['topic_id']}/split",
        json={"parts": [{"name": "P1"}, {"name": "P2"}]},
        headers=headers,
    )
    assert r.status_code == 200 and {"P1", "P2"} <= {x["name"] for x in r.json()["topics"]}
    r = pg_client.post(
        f"{base}/topics/merge",
        json={
            "topic_ids": [t["Arrays"]["topic_id"], t["Linked Lists"]["topic_id"]],
            "target_topic_id": t["Arrays"]["topic_id"],
        },
        headers=headers,
    )
    assert r.status_code == 200 and "Linked Lists" not in {x["name"] for x in r.json()["topics"]}
    assert pg_client.delete(f"{base}/topics/{t['Arrays']['topic_id']}", headers=headers).status_code == 200


def test_edit_validation_errors_are_400_and_unknown_ids_404(pg_client, pg_session, env):
    import uuid

    headers = login(pg_client, env.world.co)
    cid = _gen_via_api(pg_client, headers, env, pg_session)
    topic_id = pg_client.get(f"/teacher/curriculum/versions/{cid}").json()["topics"][0]["topic_id"]
    base = f"/teacher/curriculum/versions/{cid}"
    assert (
        pg_client.patch(f"{base}/topics/{topic_id}", json={"est_hours": -1}, headers=headers).status_code
        == 422
    )
    assert (
        pg_client.patch(
            f"{base}/topics/{topic_id}", json={"classification": "MANDATORY"}, headers=headers
        ).status_code
        == 422
    )
    assert pg_client.patch(f"{base}/topics/{topic_id}", json={}, headers=headers).status_code == 400
    # Finding D2: an explicit null is invalid input (422), never a server error.
    for body in ({"name": None}, {"unit_id": None}, {"est_hours": None}, {"outcomes": None}):
        resp = pg_client.patch(f"{base}/topics/{topic_id}", json=body, headers=headers)
        assert resp.status_code == 422, (body, resp.status_code, resp.text)
    assert (
        pg_client.patch(f"{base}/topics/{uuid.uuid4()}", json={"name": "x"}, headers=headers).status_code
        == 404
    )
    assert pg_client.delete(f"{base}/edges/{uuid.uuid4()}", headers=headers).status_code == 404


def test_edit_endpoints_reject_active_version_and_unassigned_teacher(pg_client, pg_session, env):
    owner_headers = login(pg_client, env.world.owner)
    cid = _gen_via_api(pg_client, owner_headers, env, pg_session)
    topic_id = pg_client.get(f"/teacher/curriculum/versions/{cid}").json()["topics"][0]["topic_id"]
    pg_client.post(f"/teacher/curriculum/versions/{cid}/approve", json={}, headers=owner_headers)
    r = pg_client.patch(
        f"/teacher/curriculum/versions/{cid}/topics/{topic_id}", json={"name": "late"}, headers=owner_headers
    )
    assert r.status_code == 409
    assert (
        pg_client.post(f"/teacher/curriculum/versions/{cid}/validate", headers=owner_headers).status_code
        == 409
    )
    out_headers = login(pg_client, env.world.outsider)
    assert pg_client.get(f"/teacher/curriculum/versions/{cid}").status_code == 404
    assert (
        pg_client.patch(
            f"/teacher/curriculum/versions/{cid}/topics/{topic_id}", json={"name": "x"}, headers=out_headers
        ).status_code
        == 404
    )


# ------------------------------------------------------------------ G13..G15


def test_owner_only_endpoints_role_matrix(pg_client, pg_session, env):
    co_headers = login(pg_client, env.world.co)
    cid = _gen_via_api(pg_client, co_headers, env, pg_session)
    sid = env.world.subject.id
    urls = [
        (f"/teacher/curriculum/versions/{cid}/approve", {"reason": "x"}),
        (f"/teacher/curriculum/versions/{cid}/reject", {"reason": "x"}),
        (f"/teacher/subjects/{sid}/curriculum/fallback", {"reason": "x"}),
    ]
    for url, body in urls:
        assert pg_client.post(url, json=body, headers=co_headers).status_code == 403
    out_headers = login(pg_client, env.world.outsider)
    for url, body in urls:
        assert pg_client.post(url, json=body, headers=out_headers).status_code == 404
    owner_headers = login(pg_client, env.world.owner)
    assert (
        pg_client.post(urls[0][0], json={"reason": "good"}, headers=owner_headers).json()["status"]
        == "ACTIVE"
    )
    # fallback is refused while an ACTIVE curriculum exists, even for the Owner
    assert pg_client.post(urls[2][0], json={}, headers=owner_headers).status_code == 409


def test_reject_and_fallback_over_http(pg_client, pg_session, env):
    owner_headers = login(pg_client, env.world.owner)
    cid = _gen_via_api(pg_client, owner_headers, env, pg_session)
    r = pg_client.post(
        f"/teacher/curriculum/versions/{cid}/reject", json={"reason": "unusable"}, headers=owner_headers
    )
    assert (
        r.status_code == 200
        and r.json()["status"] == "RETURNED"
        and r.json()["decision_reason"] == "unusable"
    )
    r = pg_client.post(
        f"/teacher/subjects/{env.world.subject.id}/curriculum/fallback",
        json={"reason": "no AI"},
        headers=owner_headers,
    )
    assert r.status_code == 200 and r.json()["origin"] == "FLAT_FALLBACK" and r.json()["status"] == "ACTIVE"
    graph = pg_client.get(f"/teacher/subjects/{env.world.subject.id}/curriculum/active").json()
    assert [t["name"] for t in graph["topics"]] == ["Basics", "Trees", "Graphs"] and graph["edges"] == []


def test_approve_blocked_returns_409_with_reason(pg_client, pg_session):
    setup = prepare(pg_session, threshold_active=False)
    owner_headers = login(pg_client, setup.world.owner)
    cid = _gen_via_api(pg_client, owner_headers, setup, pg_session)
    graph = pg_client.get(f"/teacher/curriculum/versions/{cid}").json()
    assert graph["can_approve"] is False and any("threshold" in b for b in graph["approval_blockers"])
    r = pg_client.post(f"/teacher/curriculum/versions/{cid}/approve", json={}, headers=owner_headers)
    assert r.status_code == 409 and "threshold" in r.json()["detail"]
    row = pg_session.get(CurriculumVersion, __import__("uuid").UUID(cid))
    assert row.status == CurriculumStatus.DRAFT


def test_no_delete_or_put_routes_for_versions(pg_client, pg_session, env):
    headers = login(pg_client, env.world.owner)
    cid = _gen_via_api(pg_client, headers, env, pg_session)
    assert pg_client.delete(f"/teacher/curriculum/versions/{cid}", headers=headers).status_code in (404, 405)
    assert pg_client.put(f"/teacher/curriculum/versions/{cid}", json={}, headers=headers).status_code in (
        404,
        405,
    )
