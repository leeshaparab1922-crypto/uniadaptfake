"""DOCX parser: python-docx paragraphs, heading styles and tables. DOCX has no
fixed pages, so the locator is the heading path plus a paragraph index
(`section:Unit 2 > Trees#p14`, ADR-0014). Embedded images are skipped."""

from __future__ import annotations

import re

from app.services.ingestion import locators
from app.services.ingestion.errors import UnreadableDocumentError
from app.services.ingestion.parsers.base import ParsedDocument, Segment

_HEADING_LEVEL = re.compile(r"^heading\s*(\d+)$", re.IGNORECASE)


def _heading_level(style_name: str) -> int | None:
    if style_name.strip().lower() == "title":
        return 1
    m = _HEADING_LEVEL.match(style_name.strip())
    return int(m.group(1)) if m else None


def parse_docx(path: str) -> ParsedDocument:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = Document(path)
    except Exception as exc:  # noqa: BLE001 - bad zip/XML
        raise UnreadableDocumentError("The DOCX file could not be read.") from exc

    segments: list[Segment] = []
    heading_stack: list[tuple[int, str]] = []
    index = 0
    try:
        for child in document.element.body.iterchildren():
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                para = Paragraph(child, document)
                text = para.text.strip()
                if not text:
                    continue
                level = _heading_level(para.style.name if para.style is not None else "")
                if level is not None:
                    while heading_stack and heading_stack[-1][0] >= level:
                        heading_stack.pop()
                    heading_stack.append((level, text))
            elif tag == "tbl":
                table = Table(child, document)
                rows = []
                for row in table.rows:
                    cells = []
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text and cell_text not in cells:
                            cells.append(cell_text)
                    if cells:
                        rows.append(" | ".join(cells))
                text = "\n".join(rows)
                if not text:
                    continue
            else:
                continue
            index += 1
            segments.append(Segment(text, locators.section([h for _, h in heading_stack], index)))
    except Exception as exc:  # noqa: BLE001
        raise UnreadableDocumentError("The DOCX file could not be read.") from exc
    return ParsedDocument(ext="docx", segments=segments)
