"""Actual-MIME detection (NFR-SEC-009; plan P-1: stdlib signature + structure
checks, no new dependency). Reads the file from disk so a 25 MB upload is never
fully loaded into memory.

A file passes only if its *content* matches the type implied by its extension;
the client-declared Content-Type must also be consistent (or generic).
"""

from __future__ import annotations

import codecs
import zipfile

from app.core.errors import ValidationError

MIME_BY_EXT = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}
_GENERIC_DECLARED = {"", "application/octet-stream", "binary/octet-stream"}
_OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
_PDF_SCAN_WINDOW = 1024


def _is_pdf(path: str) -> bool:
    with open(path, "rb") as fh:
        head = fh.read(_PDF_SCAN_WINDOW)
    return b"%PDF-" in head


def _zip_has(path: str, required_member: str) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False
    return required_member in names and "[Content_Types].xml" in names


def _is_utf8_text(path: str) -> bool:
    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
    first = True
    try:
        with open(path, "rb") as fh:
            while chunk := fh.read(1024 * 1024):
                if first and chunk.startswith(codecs.BOM_UTF8):
                    chunk = chunk[len(codecs.BOM_UTF8) :]
                first = False
                if b"\x00" in chunk:
                    return False
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        return False
    return True


def detect_actual_type(path: str) -> str | None:
    """Return the extension key (pdf, pptx, docx or txt) the *content* matches, or None."""
    if _is_pdf(path):
        return "pdf"
    if _zip_has(path, "ppt/presentation.xml"):
        return "pptx"
    if _zip_has(path, "word/document.xml"):
        return "docx"
    with open(path, "rb") as fh:
        head = fh.read(8)
    if head == _OLE_MAGIC:
        return None
    if _is_utf8_text(path):
        return "txt"
    return None


def check_archive_limits(
    path: str, *, max_uncompressed_bytes: int, max_compression_ratio: float, max_members: int
) -> None:
    """Reject a PPTX/DOCX whose ZIP contents are too large or too highly compressed
    (a "zip bomb") before any parser unpacks it (finding M5). Uses the sizes recorded
    in the ZIP directory only, so nothing is decompressed here."""
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValidationError("The file could not be read (corrupt archive).") from exc
    if len(infos) > max_members:
        raise ValidationError(f"The file contains too many parts (more than {max_members}).")
    uncompressed = sum(i.file_size for i in infos)
    compressed = sum(i.compress_size for i in infos)
    if uncompressed > max_uncompressed_bytes:
        raise ValidationError(f"The file unpacks to more than {max_uncompressed_bytes // (1024 * 1024)} MB.")
    if uncompressed > 0 and uncompressed > max_compression_ratio * max(compressed, 1):
        raise ValidationError("The file is compressed suspiciously highly and was rejected.")


def check_declared_vs_actual(path: str, ext: str, declared_content_type: str | None) -> str:
    """Raise ValidationError on a mismatch; return the validated MIME type."""
    actual = detect_actual_type(path)
    if actual != ext:
        raise ValidationError(
            f"The file content does not match its extension (declared .{ext}). "
            f"Upload a valid {ext.upper()} file."
        )
    expected_mime = MIME_BY_EXT[ext]
    declared = (declared_content_type or "").split(";")[0].strip().lower()
    if declared not in _GENERIC_DECLARED and declared != expected_mime:
        raise ValidationError("The declared content type does not match the file content.")
    return expected_mime
