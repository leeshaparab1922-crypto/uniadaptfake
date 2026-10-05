"""PDF parser: pdfplumber text per page; pypdfium2 renders pages at a fixed DPI
for Tesseract (ADR-0013/0014). Locator `page:<n>` (1-based)."""

from __future__ import annotations

import io

from app.services.ingestion import locators
from app.services.ingestion.errors import UnreadableDocumentError
from app.services.ingestion.parsers.base import ParsedDocument, Segment, non_whitespace_chars


def parse_pdf(path: str, *, min_page_chars: int, render_dpi: int, max_pages: int) -> ParsedDocument:
    import pdfplumber
    import pypdfium2 as pdfium

    segments: list[Segment] = []
    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) == 0:
                raise UnreadableDocumentError("The PDF has no pages.")
            if len(pdf.pages) > max_pages:
                raise UnreadableDocumentError(
                    f"The PDF has {len(pdf.pages)} pages; the limit is {max_pages}. "
                    "Split it and upload again."
                )
            for index, pdf_page in enumerate(pdf.pages, start=1):
                text = pdf_page.extract_text() or ""
                needs_ocr = non_whitespace_chars(text) < min_page_chars
                segments.append(Segment(text, locators.page(index), page_no=index, needs_ocr=needs_ocr))
    except UnreadableDocumentError:
        raise
    except Exception as exc:  # noqa: BLE001 - any parser failure means "unreadable" (Section 17)
        raise UnreadableDocumentError("The PDF could not be read (corrupt or password protected).") from exc

    state: dict[str, pdfium.PdfDocument] = {}

    def render_png(page_no: int) -> bytes:
        if "doc" not in state:
            state["doc"] = pdfium.PdfDocument(path)
        doc = state["doc"]
        image = doc[page_no - 1].render(scale=render_dpi / 72.0).to_pil().convert("RGB")
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

    def _close() -> None:
        doc = state.pop("doc", None)
        if doc is not None:
            doc.close()

    parsed = ParsedDocument(ext="pdf", segments=segments, render_png=render_png)
    parsed._closers.append(_close)
    return parsed
