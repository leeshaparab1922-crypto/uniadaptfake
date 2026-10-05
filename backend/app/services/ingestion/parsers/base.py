"""Parser result types and dispatch (ADR-0014)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segment:
    """One source-located piece of extracted text (a PDF page, a slide, a DOCX
    paragraph, a TXT paragraph). `needs_ocr` marks a PDF page with no usable text."""

    text: str
    locator: str
    page_no: int | None = None
    needs_ocr: bool = False


@dataclass
class ParsedDocument:
    ext: str
    segments: list[Segment]
    # Only PDFs can be rasterised for OCR (scanned pages are supplied as PDF).
    render_png: Callable[[int], bytes] | None = None
    _closers: list[Callable[[], None]] = field(default_factory=list)

    def close(self) -> None:
        for closer in self._closers:
            try:
                closer()
            except Exception:  # noqa: BLE001 - closing must never mask the real error
                pass
        self._closers.clear()


def non_whitespace_chars(text: str) -> int:
    return sum(1 for ch in text if not ch.isspace())


def parse_document(
    path: str,
    ext: str,
    *,
    min_page_chars: int,
    render_dpi: int,
    include_pptx_notes: bool,
    max_pdf_pages: int = 500,
) -> ParsedDocument:
    """Open and extract `path` according to its validated extension."""
    # Imported lazily so unit tests of one format do not require the others' libraries.
    if ext == "pdf":
        from app.services.ingestion.parsers.pdf import parse_pdf

        return parse_pdf(path, min_page_chars=min_page_chars, render_dpi=render_dpi, max_pages=max_pdf_pages)
    if ext == "pptx":
        from app.services.ingestion.parsers.pptx import parse_pptx

        return parse_pptx(path, include_notes=include_pptx_notes)
    if ext == "docx":
        from app.services.ingestion.parsers.docx import parse_docx

        return parse_docx(path)
    if ext == "txt":
        from app.services.ingestion.parsers.txt import parse_txt

        return parse_txt(path)
    raise ValueError(f"Unsupported extension: {ext}")
