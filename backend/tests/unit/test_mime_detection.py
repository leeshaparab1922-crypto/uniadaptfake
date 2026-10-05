"""NFR-SEC-009: declared vs actual MIME (stdlib signature/structure checks, plan P-1)."""

from __future__ import annotations

import pytest

from app.core.errors import ValidationError
from app.services.ingestion import mime
from tests.support import docs


def _write(tmp_path, name, data: bytes) -> str:
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


def test_real_files_of_each_type_detected(tmp_path):
    assert mime.detect_actual_type(_write(tmp_path, "a.pdf", docs.make_text_pdf([["hi"]]))) == "pdf"
    assert (
        mime.detect_actual_type(_write(tmp_path, "a.docx", docs.make_docx([("Normal", "hello")]))) == "docx"
    )
    assert mime.detect_actual_type(_write(tmp_path, "a.pptx", docs.make_pptx([("t", None)]))) == "pptx"
    assert mime.detect_actual_type(_write(tmp_path, "a.txt", "héllo".encode())) == "txt"


def test_declared_pdf_but_zip_content_rejected(tmp_path):
    path = _write(tmp_path, "fake.pdf", docs.make_docx([("Normal", "x")]))
    with pytest.raises(ValidationError, match="does not match"):
        mime.check_declared_vs_actual(path, "pdf", None)


def test_declared_docx_but_pptx_content_rejected(tmp_path):
    path = _write(tmp_path, "fake.docx", docs.make_pptx([("t", None)]))
    with pytest.raises(ValidationError):
        mime.check_declared_vs_actual(path, "docx", None)


def test_legacy_ole_renamed_to_docx_rejected(tmp_path):
    path = _write(tmp_path, "old.docx", docs.make_legacy_ole())
    with pytest.raises(ValidationError):
        mime.check_declared_vs_actual(path, "docx", None)


def test_executable_renamed_to_pdf_rejected(tmp_path):
    path = _write(tmp_path, "evil.pdf", b"MZ\x90\x00\x03\x00\x00\x00" + b"\xff" * 200)
    with pytest.raises(ValidationError):
        mime.check_declared_vs_actual(path, "pdf", None)


def test_non_utf8_text_rejected(tmp_path):
    path = _write(tmp_path, "latin.txt", "café".encode("latin-1"))
    with pytest.raises(ValidationError):
        mime.check_declared_vs_actual(path, "txt", None)


def test_txt_with_nul_bytes_rejected(tmp_path):
    path = _write(tmp_path, "bin.txt", b"hello\x00world")
    with pytest.raises(ValidationError):
        mime.check_declared_vs_actual(path, "txt", None)


def test_utf8_bom_text_accepted(tmp_path):
    path = _write(tmp_path, "bom.txt", b"\xef\xbb\xbfhello")
    assert mime.check_declared_vs_actual(path, "txt", "text/plain") == "text/plain"


def test_client_declared_content_type_mismatch_rejected(tmp_path):
    path = _write(tmp_path, "a.pdf", docs.make_text_pdf([["hi"]]))
    with pytest.raises(ValidationError, match="declared content type"):
        mime.check_declared_vs_actual(path, "pdf", "image/png")


def test_generic_declared_type_allowed(tmp_path):
    path = _write(tmp_path, "a.pdf", docs.make_text_pdf([["hi"]]))
    assert mime.check_declared_vs_actual(path, "pdf", "application/octet-stream") == "application/pdf"
