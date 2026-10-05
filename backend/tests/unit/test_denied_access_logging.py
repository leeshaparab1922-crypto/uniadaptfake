"""Section 37 unauthorized access (findings m5/N8): denials are logged with ids only."""

from __future__ import annotations

import logging
import uuid
from types import SimpleNamespace

from app.services.content_service import _log_denied


def test_denial_log_has_reason_and_ids_but_no_personal_data(caplog):
    teacher = SimpleNamespace(id=uuid.uuid4(), email="t@example.edu", full_name="Teacher Name")
    link_id = uuid.uuid4()
    with caplog.at_level(logging.WARNING, logger="app.services.content_service"):
        _log_denied(teacher, "link_not_assigned_or_missing", link_id=link_id)
    (record,) = caplog.records
    message = record.getMessage()
    assert "reason=link_not_assigned_or_missing" in message
    assert str(teacher.id) in message and f"link_id={link_id}" in message
    assert "example.edu" not in message and "Teacher Name" not in message
