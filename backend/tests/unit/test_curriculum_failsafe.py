"""Verification findings D1 (generation never stays GENERATING) and D2 (explicit nulls). No services."""

from __future__ import annotations

import uuid

import pytest
from celery.exceptions import Retry, SoftTimeLimitExceeded
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings
from app.core.errors import ValidationError
from app.schemas.curriculum import TopicPatch


def test_curriculum_limits_are_sized_to_the_llm_call_budget():
    s = Settings()
    calls = 1 + s.llm_repair_attempts
    assert s.effective_curriculum_soft_time_limit_seconds == s.llm_request_timeout_seconds * calls + 300
    assert s.effective_curriculum_time_limit_seconds == s.effective_curriculum_soft_time_limit_seconds + 300
    assert s.effective_curriculum_stale_after_seconds == s.effective_curriculum_time_limit_seconds + 1200
    custom = Settings(
        curriculum_generation_stale_after_seconds=60, curriculum_task_soft_time_limit_seconds=90
    )
    assert custom.effective_curriculum_stale_after_seconds == 60
    assert custom.effective_curriculum_soft_time_limit_seconds == 90


def test_curriculum_task_has_its_own_time_limits():
    from app.core.config import settings
    from app.workers.curriculum_tasks import generate_curriculum

    assert generate_curriculum.soft_time_limit == settings.effective_curriculum_soft_time_limit_seconds
    assert generate_curriculum.time_limit == settings.effective_curriculum_time_limit_seconds


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch(monkeypatch, exc):
    from app.workers import curriculum_tasks

    failed: list[tuple[uuid.UUID, str]] = []
    monkeypatch.setattr(curriculum_tasks, "SessionLocal", _Session)
    monkeypatch.setattr(curriculum_tasks, "build_provider", lambda name: object())
    monkeypatch.setattr(curriculum_tasks, "_get_embedder", lambda: object())

    def boom(*args, **kwargs):
        raise exc

    monkeypatch.setattr(curriculum_tasks, "run_generation", boom)
    monkeypatch.setattr(
        curriculum_tasks, "mark_generation_failed", lambda db, vid, msg, **kw: failed.append((vid, msg))
    )
    return curriculum_tasks, failed


@pytest.mark.parametrize(
    "exc,reason",
    [
        (RuntimeError("prompt registry out of sync"), "unexpected_error"),
        (ValueError("unknown LLM provider"), "unexpected_error"),
        (SoftTimeLimitExceeded(), "time_limit"),
    ],
)
def test_any_failure_ends_as_generation_failed(monkeypatch, exc, reason):
    tasks, failed = _patch(monkeypatch, exc)
    vid = str(uuid.uuid4())
    result = tasks.generate_curriculum.run(vid)
    assert result == {"status": "GENERATION_FAILED", "reason": reason}
    expected = tasks.TIME_LIMIT_MESSAGE if reason == "time_limit" else tasks.UNEXPECTED_MESSAGE
    assert failed == [(uuid.UUID(vid), expected)]


def test_time_limit_hidden_behind_another_error_is_still_a_time_limit(monkeypatch):
    try:
        try:
            raise SoftTimeLimitExceeded()
        except SoftTimeLimitExceeded:
            raise RuntimeError("session is in an inactive transaction")  # noqa: B904
    except RuntimeError as chained:
        exc = chained
    tasks, failed = _patch(monkeypatch, exc)
    assert tasks.generate_curriculum.run(str(uuid.uuid4()))["reason"] == "time_limit"
    assert failed and failed[0][1] == tasks.TIME_LIMIT_MESSAGE


def test_celery_retry_is_not_swallowed(monkeypatch):
    tasks, failed = _patch(monkeypatch, Retry("provider outage"))
    with pytest.raises(Retry):
        tasks.generate_curriculum.run(str(uuid.uuid4()))
    assert failed == []


@pytest.mark.parametrize(
    "field", ["name", "classification", "est_hours", "outcomes", "bloom_level", "unit_id"]
)
def test_topic_patch_rejects_explicit_null(field):
    with pytest.raises(PydanticValidationError, match="cannot be null"):
        TopicPatch.model_validate({field: None})


def test_topic_patch_omitted_fields_are_not_nulls():
    assert TopicPatch.model_validate({"name": "Trees"}).model_dump(exclude_unset=True) == {"name": "Trees"}


def test_update_topic_rejects_nulls_before_touching_the_database():
    from app.services.curriculum_edit_service import update_topic

    with pytest.raises(ValidationError, match="cannot be null"):
        update_topic(
            None,  # type: ignore[arg-type]  # never reached: validation happens first
            actor=None,  # type: ignore[arg-type]
            curriculum_version_id=uuid.uuid4(),
            topic_id=uuid.uuid4(),
            changes={"name": None},
            embedder=None,  # type: ignore[arg-type]
        )
