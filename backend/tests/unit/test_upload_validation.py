"""FR-CON-001 validation: extension, size, non-empty, HTTPS links. NFR-SEC-009."""

from __future__ import annotations

import pytest

from app.core.errors import PayloadTooLargeError, ValidationError
from app.services.ingestion import validators

MAX = 25 * 1024 * 1024


@pytest.mark.parametrize(
    "name,ext", [("a.pdf", "pdf"), ("Notes.PPTX", "pptx"), ("x.y.docx", "docx"), ("t.TXT", "txt")]
)
def test_supported_extensions_accepted_case_insensitively(name, ext):
    assert validators.validate_extension(name) == ext


@pytest.mark.parametrize("name", ["old.doc", "old.ppt"])
def test_rejects_legacy_doc_ppt(name):
    with pytest.raises(ValidationError, match="Legacy"):
        validators.validate_extension(name)


@pytest.mark.parametrize("name", ["scan.png", "scan.JPG", "scan.tiff"])
def test_rejects_direct_image_uploads(name):
    with pytest.raises(ValidationError, match="PDF"):
        validators.validate_extension(name)


@pytest.mark.parametrize("name", ["run.exe", "x.sh", "evil.js", "a.bat"])
def test_rejects_executables(name):
    with pytest.raises(ValidationError, match="Executable"):
        validators.validate_extension(name)


@pytest.mark.parametrize("name", [None, "", "noextension", ".hidden"])
def test_rejects_missing_or_unknown_extension(name):
    with pytest.raises(ValidationError):
        validators.validate_extension(name)


def test_25mb_boundary_accepts_exact_and_rejects_plus_one():
    validators.validate_size(MAX, MAX)
    with pytest.raises(PayloadTooLargeError):
        validators.validate_size(MAX + 1, MAX)


def test_zero_byte_file_rejected():
    with pytest.raises(ValidationError, match="empty"):
        validators.validate_size(0, MAX)


def test_filename_is_sanitised_for_display_only():
    assert validators.safe_display_filename("..\\..\\etc/passwd\x00.pdf") == "passwd.pdf"
    assert len(validators.safe_display_filename("a" * 400 + ".pdf")) == 255


def test_https_link_accepted():
    assert validators.validate_https_url(" https://example.com/a?b=1 ") == "https://example.com/a?b=1"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "ftp://example.com",
        "//example.com",
        "https://",
        "https://user:pw@example.com",
        "https://exa mple.com",
        "",
        None,
        "https://example.com/" + "a" * 2100,
    ],
)
def test_http_javascript_and_file_scheme_links_rejected(url):
    with pytest.raises(ValidationError):
        validators.validate_https_url(url)


def test_blank_title_rejected_and_control_chars_stripped():
    with pytest.raises(ValidationError):
        validators.validate_title("   \x00 ")
    assert validators.validate_title("  Good\x07 title ") == "Good title"
