"""Section 43 Phase 1 'seed' deliverable: re-running the seed script must
not duplicate or corrupt records."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.seed_demo_data import seed  # noqa: E402


def test_seed_is_idempotent_and_consistent(db_session):
    seed(db_session)

    from app.models.subject import Subject
    from app.models.subject_instance import SubjectInstance
    from app.models.user import User

    first_user_count = db_session.query(User).count()
    first_subject_count = db_session.query(Subject).count()
    first_instance_count = db_session.query(SubjectInstance).count()

    seed(db_session)

    assert db_session.query(User).count() == first_user_count
    assert db_session.query(Subject).count() == first_subject_count
    assert db_session.query(SubjectInstance).count() == first_instance_count


def test_seed_creates_expected_core_entities(db_session):
    seed(db_session)

    from app.models.subject import Subject, SubjectType
    from app.models.user import User, UserRole

    assert db_session.query(User).filter(User.role == UserRole.ADMIN).count() >= 1
    assert db_session.query(User).filter(User.role == UserRole.TEACHER).count() >= 1
    assert db_session.query(User).filter(User.role == UserRole.STUDENT).count() >= 1
    assert db_session.query(Subject).filter(Subject.type == SubjectType.LAB).count() >= 1
    assert db_session.query(Subject).filter(Subject.type == SubjectType.ELECTIVE).count() >= 1
