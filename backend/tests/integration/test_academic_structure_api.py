"""FR-ADM-001 hierarchy list (view) endpoints."""

from __future__ import annotations

import datetime as dt

import pytest

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services import academic_structure_service as svc

BASE = "/admin/academic-structure"


def _user(db, email, role):
    u = User(
        email=email,
        full_name="U",
        password_hash=hash_password("Secret123!"),
        role=role,
        is_active=True,
        token_version=0,
    )
    db.add(u)
    db.commit()
    return u


def _login(client, email):
    resp = client.post("/auth/login", json={"email": email, "password": "Secret123!"})
    assert resp.status_code == 200


@pytest.fixture()
def admin_client(client, db_session):
    admin = _user(db_session, "ladmin@example.com", UserRole.ADMIN)
    _login(client, "ladmin@example.com")
    return client, admin


def test_lists_each_level_with_parent_filter_and_ordering(admin_client, db_session):
    client, admin = admin_client
    # Created out of natural order to prove ordering is applied.
    inst_b = svc.create_institute(db_session, actor=admin, name="Beta", timezone="UTC")
    inst_a = svc.create_institute(db_session, actor=admin, name="Alpha", timezone="UTC")
    d_mech = svc.create_department(db_session, actor=admin, institute_id=inst_a.id, code="MECH", name="M")
    d_cse = svc.create_department(db_session, actor=admin, institute_id=inst_a.id, code="CSE", name="C")
    svc.create_department(db_session, actor=admin, institute_id=inst_b.id, code="ECE", name="E")
    p2 = svc.create_program(
        db_session, actor=admin, department_id=d_cse.id, code="MT", name="M", duration_semesters=4
    )
    p1 = svc.create_program(
        db_session, actor=admin, department_id=d_cse.id, code="BT", name="B", duration_semesters=8
    )
    svc.create_program(
        db_session, actor=admin, department_id=d_mech.id, code="BT", name="B", duration_semesters=8
    )
    b2 = svc.create_batch(db_session, actor=admin, program_id=p1.id, start_year=2025, end_year=2029)
    b1 = svc.create_batch(db_session, actor=admin, program_id=p1.id, start_year=2024, end_year=2028)
    svc.create_batch(db_session, actor=admin, program_id=p2.id, start_year=2024, end_year=2026)
    s2 = svc.create_semester(
        db_session,
        actor=admin,
        batch_id=b1.id,
        number=2,
        start_date=dt.date(2025, 1, 1),
        end_date=dt.date(2025, 5, 1),
    )
    s1 = svc.create_semester(
        db_session,
        actor=admin,
        batch_id=b1.id,
        number=1,
        start_date=dt.date(2024, 8, 1),
        end_date=dt.date(2024, 12, 1),
    )
    svc.create_semester(
        db_session,
        actor=admin,
        batch_id=b2.id,
        number=1,
        start_date=dt.date(2025, 8, 1),
        end_date=dt.date(2025, 12, 1),
    )
    svc.create_section(db_session, actor=admin, semester_id=s1.id, name="B", capacity=60)
    svc.create_section(db_session, actor=admin, semester_id=s1.id, name="A", capacity=60)
    svc.create_section(db_session, actor=admin, semester_id=s2.id, name="A", capacity=60)

    r = client.get(f"{BASE}/institutes")
    assert r.status_code == 200
    assert [i["name"] for i in r.json()] == ["Alpha", "Beta"]

    r = client.get(f"{BASE}/departments", params={"institute_id": str(inst_a.id)})
    assert [d["code"] for d in r.json()] == ["CSE", "MECH"]
    assert len(client.get(f"{BASE}/departments").json()) == 3

    r = client.get(f"{BASE}/programs", params={"department_id": str(d_cse.id)})
    assert [p["code"] for p in r.json()] == ["BT", "MT"]

    r = client.get(f"{BASE}/batches", params={"program_id": str(p1.id)})
    assert [b["start_year"] for b in r.json()] == [2024, 2025]

    r = client.get(f"{BASE}/semesters", params={"batch_id": str(b1.id)})
    assert [s["number"] for s in r.json()] == [1, 2]

    r = client.get(f"{BASE}/sections", params={"semester_id": str(s1.id)})
    assert [s["name"] for s in r.json()] == ["A", "B"]
    assert set(r.json()[0]) == {"id", "semester_id", "name", "capacity"}


def test_empty_and_unknown_parent_return_empty_list(admin_client):
    client, _ = admin_client
    assert client.get(f"{BASE}/institutes").json() == []
    r = client.get(f"{BASE}/departments", params={"institute_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 200 and r.json() == []


def test_invalid_parent_id_is_422(admin_client):
    client, _ = admin_client
    assert client.get(f"{BASE}/departments", params={"institute_id": "nope"}).status_code == 422


LEVELS = ["institutes", "departments", "programs", "batches", "semesters", "sections"]


@pytest.mark.parametrize("level", LEVELS)
def test_unauthenticated_is_401(client, level):
    assert client.get(f"{BASE}/{level}").status_code == 401


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.STUDENT])
@pytest.mark.parametrize("level", LEVELS)
def test_non_admin_is_403(client, db_session, role, level):
    _user(db_session, f"x-{role.value.lower()}@example.com", role)
    _login(client, f"x-{role.value.lower()}@example.com")
    assert client.get(f"{BASE}/{level}").status_code == 403
