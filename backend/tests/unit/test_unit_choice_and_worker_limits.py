"""Finding m2 upload Unit choice, and finding M5 worker time limits. No services."""

from __future__ import annotations

import uuid

import pytest
from celery.exceptions import SoftTimeLimitExceeded

from app.core.errors import ValidationError
from app.models.content import ContentType
from app.services.content_service import _check_unit_choice
from app.services.ingestion.errors import TransientIngestionError

UNIT = uuid.uuid4()


@pytest.mark.parametrize(
    "content_type", [ContentType.NOTES, ContentType.PPT, ContentType.PYQ, ContentType.LAB]
)
def test_non_syllabus_upload_must_choose_a_unit_or_all_units(content_type):
    with pytest.raises(ValidationError, match="Choose the Unit"):
        _check_unit_choice(content_type, None, False)
    _check_unit_choice(content_type, UNIT, False)
    _check_unit_choice(content_type, None, True)


def test_unit_and_all_units_together_is_rejected():
    with pytest.raises(ValidationError, match="not both"):
        _check_unit_choice(ContentType.NOTES, UNIT, True)


def test_syllabus_needs_no_unit_choice():
    _check_unit_choice(ContentType.SYLLABUS, None, False)
    _check_unit_choice(ContentType.SYLLABUS, None, True)


def test_syllabus_with_a_single_unit_is_rejected():
    """Finding N4: a syllabus always covers all Units (Units come from its headings)."""
    with pytest.raises(ValidationError, match="covers all Units"):
        _check_unit_choice(ContentType.SYLLABUS, UNIT, False)


def test_celery_has_the_configured_time_limits():
    from app.workers.celery_app import celery_app

    assert celery_app.conf.task_soft_time_limit == 25 * 60
    assert celery_app.conf.task_time_limit == 30 * 60
    assert celery_app.conf.task_acks_late is True


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_task(monkeypatch, raise_exc):
    from app.workers import ingestion_tasks

    marked: list[str] = []
    monkeypatch.setattr(ingestion_tasks, "_adapters", lambda: dict(store=1, ocr=1, tokenizer=1, embedder=1))
    monkeypatch.setattr(ingestion_tasks, "SessionLocal", _Session)

    def boom(*args, **kwargs):
        raise raise_exc

    monkeypatch.setattr(ingestion_tasks, "ingest_version", boom)
    monkeypatch.setattr(ingestion_tasks, "mark_timed_out", lambda db, vid: marked.append(vid))
    return ingestion_tasks, marked


def test_soft_time_limit_marks_the_version_failed_without_retrying(monkeypatch):
    tasks, marked = _patch_task(monkeypatch, SoftTimeLimitExceeded())
    result = tasks.ingest_content_version.run("v-1")
    assert result["status"] == "FAILED" and result["reason"] == "time_limit" and marked == ["v-1"]


def test_soft_time_limit_wrapped_by_a_stage_is_also_not_retried(monkeypatch):
    wrapped = TransientIngestionError("retry")
    wrapped.__cause__ = SoftTimeLimitExceeded()
    tasks, marked = _patch_task(monkeypatch, wrapped)
    result = tasks.ingest_content_version.run("v-2")
    assert result["reason"] == "time_limit" and marked == ["v-2"]


def test_other_transient_errors_are_still_raised_for_celery_to_retry(monkeypatch):
    tasks, marked = _patch_task(monkeypatch, TransientIngestionError("object store down"))
    with pytest.raises(TransientIngestionError):
        tasks.ingest_content_version.run("v-3")
    assert marked == []


def test_time_limit_hidden_behind_a_database_error_is_not_retried(monkeypatch):
    """Finding N3: the signal can fire mid-write, leaving it only as the context of a DB error."""
    try:
        try:
            raise SoftTimeLimitExceeded()
        except SoftTimeLimitExceeded:
            raise RuntimeError("session is in an inactive transaction")  # noqa: B904
    except RuntimeError as db_error:
        chained = db_error
    tasks, marked = _patch_task(monkeypatch, chained)
    result = tasks.ingest_content_version.run("v-4")
    assert result["reason"] == "time_limit" and marked == ["v-4"]


def test_unrelated_errors_are_not_mistaken_for_a_time_limit(monkeypatch):
    tasks, marked = _patch_task(monkeypatch, RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        tasks.ingest_content_version.run("v-5")
    assert marked == []
