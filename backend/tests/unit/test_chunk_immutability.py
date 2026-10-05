"""FR-CON-003: chunks are insert-only (static check over application code; no services needed)."""

from __future__ import annotations


def test_chunk_rows_are_insert_only_in_service_code():
    """No application module updates a chunk's text/locator/metadata; only the embedding column is
    filled in by the ingestion repository while the version is still DRAFT/RUNNING."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[2] / "app"
    offenders = []
    for path in root.rglob("*.py"):
        src = path.read_text(encoding="utf-8")
        for m in re.finditer(r"update\(ContentChunk\)[\s\S]{0,300}?\.values\(([^)]*)\)", src):
            if m.group(1).strip() != "embedding=vector":
                offenders.append((str(path), m.group(1)))
    assert offenders == []
