"""When may a Teacher retry ingestion of a DRAFT version? (finding M2, BUS-040, Section 37)

Human decision 2026-10-04: any assigned Teacher may retry
- a FAILED version at once,
- a PENDING version at once (e.g. the queue was down at upload time),
- a RUNNING version only once it has shown no activity for longer than the
  configured timeout (default: job time limit + 10 minutes), i.e. its worker
  is presumed dead.
A SUCCEEDED version is never re-ingested. Pure function, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class RetryWindow:
    can_retry: bool
    available_at: datetime | None  # when a RUNNING version becomes retryable; None otherwise


def retry_window(
    *,
    version_status: str,
    ingestion_status: str,
    heartbeat_at: datetime | None,
    now: datetime,
    stale_after_seconds: int,
) -> RetryWindow:
    if version_status != "DRAFT":
        return RetryWindow(False, None)
    if ingestion_status in ("FAILED", "PENDING"):
        return RetryWindow(True, None)
    if ingestion_status == "RUNNING":
        if heartbeat_at is None:
            return RetryWindow(True, None)
        available_at = heartbeat_at + timedelta(seconds=stale_after_seconds)
        return RetryWindow(now >= available_at, available_at)
    return RetryWindow(False, None)


def is_stale_running(
    *, ingestion_status: str, heartbeat_at: datetime | None, now: datetime, stale_after_seconds: int
) -> bool:
    """True when a RUNNING version's worker is presumed dead (no activity within the timeout)."""
    if ingestion_status != "RUNNING":
        return False
    if heartbeat_at is None:
        return True
    return now >= heartbeat_at + timedelta(seconds=stale_after_seconds)
