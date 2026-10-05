"""Upload/link validation (FR-CON-001, SRS Section 17, NFR-SEC-009). Pure functions."""

from __future__ import annotations

import posixpath
import re
from urllib.parse import urlsplit

from app.core.errors import PayloadTooLargeError, ValidationError

ALLOWED_EXTENSIONS = ("pdf", "pptx", "docx", "txt")
LEGACY_EXTENSIONS = {"doc", "ppt", "xls"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tif", "tiff", "webp", "heic", "svg"}
EXECUTABLE_EXTENSIONS = {
    "exe",
    "dll",
    "bat",
    "cmd",
    "com",
    "msi",
    "sh",
    "js",
    "jar",
    "apk",
    "scr",
    "ps1",
    "vbs",
}
MAX_FILENAME_LENGTH = 255
MAX_URL_LENGTH = 2048
MAX_TITLE_LENGTH = 255
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def safe_display_filename(raw: str | None) -> str:
    """Original filename for display only (never used in object keys - ADR-0018)."""
    name = posixpath.basename((raw or "").replace("\\", "/")).strip()
    name = _CONTROL_CHARS.sub("", name)
    return name[:MAX_FILENAME_LENGTH]


def validate_extension(filename: str | None) -> str:
    name = safe_display_filename(filename)
    if not name or "." not in name:
        raise ValidationError("File must have an extension: PDF, PPTX, DOCX or TXT.")
    ext = name.rsplit(".", 1)[1].lower()
    if ext in ALLOWED_EXTENSIONS:
        return ext
    if ext in LEGACY_EXTENSIONS:
        raise ValidationError(
            "Legacy .doc/.ppt files are not supported. Save as DOCX/PPTX or PDF and upload again."
        )
    if ext in IMAGE_EXTENSIONS:
        raise ValidationError("Image uploads are not supported. Supply scanned pages as a PDF.")
    if ext in EXECUTABLE_EXTENSIONS:
        raise ValidationError("Executable files are not allowed.")
    raise ValidationError("Unsupported file type. Allowed: PDF, PPTX, DOCX, TXT.")


def validate_size(size_bytes: int, max_bytes: int) -> None:
    if size_bytes <= 0:
        raise ValidationError("The file is empty.")
    if size_bytes > max_bytes:
        raise PayloadTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.")


def validate_title(title: str | None, *, what: str = "Title") -> str:
    cleaned = _CONTROL_CHARS.sub("", (title or "")).strip()
    if not cleaned:
        raise ValidationError(f"{what} is required.")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValidationError(f"{what} must be at most {MAX_TITLE_LENGTH} characters.")
    return cleaned


def validate_https_url(url: str | None) -> str:
    """NFR-SEC-009: recommendation links must be HTTPS. The URL is never fetched."""
    candidate = (url or "").strip()
    if not candidate:
        raise ValidationError("Link URL is required.")
    if len(candidate) > MAX_URL_LENGTH or re.search(r"\s", candidate) or _CONTROL_CHARS.search(candidate):
        raise ValidationError("Link URL is invalid.")
    parts = urlsplit(candidate)
    if parts.scheme.lower() != "https":
        raise ValidationError("Only HTTPS links are allowed.")
    if not parts.hostname or parts.username or parts.password:
        raise ValidationError("Link URL is invalid.")
    return candidate
