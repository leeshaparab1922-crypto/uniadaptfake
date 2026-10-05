"""Finding M5: PPTX/DOCX zip-bomb limits, checked from the ZIP directory without unpacking."""

from __future__ import annotations

import zipfile

import pytest

from app.core.errors import ValidationError
from app.services.ingestion.mime import check_archive_limits
from tests.support import docs

LIMITS = dict(max_uncompressed_bytes=1_000_000, max_compression_ratio=100.0, max_members=50)


def _zip(tmp_path, members: dict[str, bytes], name="f.docx"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for member, data in members.items():
            zf.writestr(member, data)
    return str(path)


def test_real_docx_and_pptx_pass_the_default_limits(tmp_path):
    for name, data in (
        ("a.docx", docs.make_docx([("Normal", "hello")])),
        ("a.pptx", docs.make_pptx([("Slide text", None)])),
    ):
        path = tmp_path / name
        path.write_bytes(data)
        check_archive_limits(
            str(path),
            max_uncompressed_bytes=200 * 1024 * 1024,
            max_compression_ratio=100.0,
            max_members=2000,
        )


def test_too_many_members_rejected(tmp_path):
    path = _zip(tmp_path, {f"part{i}.xml": b"<a/>" for i in range(51)})
    with pytest.raises(ValidationError, match="too many parts"):
        check_archive_limits(path, **LIMITS)


def test_uncompressed_size_over_limit_rejected(tmp_path):
    import os

    path = _zip(tmp_path, {"big.bin": os.urandom(1_000_001)})
    with pytest.raises(ValidationError, match="unpacks to more than"):
        check_archive_limits(path, **LIMITS)


def test_highly_compressed_content_rejected(tmp_path):
    path = _zip(tmp_path, {"zeros.xml": b"\0" * 900_000})
    with pytest.raises(ValidationError, match="compressed suspiciously"):
        check_archive_limits(path, **LIMITS)


def test_corrupt_archive_rejected(tmp_path):
    path = tmp_path / "bad.docx"
    path.write_bytes(b"PK\x03\x04 not really a zip")
    with pytest.raises(ValidationError, match="could not be read"):
        check_archive_limits(str(path), **LIMITS)
