"""Finding M2 retry rule (human decision 2026-10-04) and its settings. Pure, no services."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.services.ingestion_retry import is_stale_running, retry_window

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
STALE = 40 * 60


def _window(status="DRAFT", ingestion="FAILED", heartbeat=None, now=NOW):
    return retry_window(
        version_status=status,
        ingestion_status=ingestion,
        heartbeat_at=heartbeat,
        now=now,
        stale_after_seconds=STALE,
    )


@pytest.mark.parametrize("ingestion", ["FAILED", "PENDING"])
def test_failed_and_pending_drafts_can_retry_at_once(ingestion):
    w = _window(ingestion=ingestion, heartbeat=NOW)
    assert w.can_retry and w.available_at is None


def test_running_with_recent_activity_cannot_retry_and_reports_when_it_can():
    w = _window(ingestion="RUNNING", heartbeat=NOW - timedelta(minutes=5))
    assert not w.can_retry
    assert w.available_at == NOW - timedelta(minutes=5) + timedelta(seconds=STALE)


def test_running_becomes_retryable_exactly_at_the_timeout():
    heartbeat = NOW - timedelta(seconds=STALE)
    assert _window(ingestion="RUNNING", heartbeat=heartbeat).can_retry
    assert not _window(ingestion="RUNNING", heartbeat=heartbeat + timedelta(seconds=1)).can_retry


def test_running_without_any_heartbeat_is_treated_as_stale():
    assert _window(ingestion="RUNNING", heartbeat=None).can_retry


def test_succeeded_never_retries():
    assert not _window(ingestion="SUCCEEDED").can_retry


@pytest.mark.parametrize("status", ["ACTIVE", "SUPERSEDED"])
def test_non_draft_versions_never_retry(status):
    assert not _window(status=status, ingestion="FAILED").can_retry


def test_is_stale_running():
    old = NOW - timedelta(seconds=STALE + 1)
    assert is_stale_running(ingestion_status="RUNNING", heartbeat_at=old, now=NOW, stale_after_seconds=STALE)
    assert not is_stale_running(
        ingestion_status="RUNNING", heartbeat_at=NOW, now=NOW, stale_after_seconds=STALE
    )
    assert is_stale_running(ingestion_status="RUNNING", heartbeat_at=None, now=NOW, stale_after_seconds=STALE)
    assert not is_stale_running(
        ingestion_status="FAILED", heartbeat_at=old, now=NOW, stale_after_seconds=STALE
    )


def test_default_stale_timeout_is_time_limit_plus_ten_minutes():
    s = Settings()
    assert s.ingest_task_time_limit_seconds == 30 * 60
    assert s.ingest_task_soft_time_limit_seconds == 25 * 60
    assert s.effective_ingest_stale_after_seconds == 40 * 60
    assert Settings(ingest_stale_after_seconds=90).effective_ingest_stale_after_seconds == 90


def test_m5_limit_defaults():
    s = Settings()
    assert s.ingest_max_pdf_pages == 500
    assert s.ingest_archive_max_uncompressed_bytes == 200 * 1024 * 1024
    assert s.ingest_archive_max_compression_ratio == 100.0
    assert s.ingest_archive_max_members == 2000
