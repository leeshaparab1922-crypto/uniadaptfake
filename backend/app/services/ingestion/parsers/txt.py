"""TXT parser: standard library, strict UTF-8 (ADR-0014). Locator `lines:a-b`."""

from __future__ import annotations

from app.services.ingestion import locators
from app.services.ingestion.errors import UnreadableDocumentError
from app.services.ingestion.parsers.base import ParsedDocument, Segment


def parse_txt(path: str) -> ParsedDocument:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        text = raw.decode("utf-8-sig", errors="strict")  # a leading BOM is tolerated
    except UnicodeDecodeError as exc:
        raise UnreadableDocumentError("The TXT file is not valid UTF-8.") from exc
    except OSError as exc:
        raise UnreadableDocumentError("The TXT file could not be read.") from exc

    segments: list[Segment] = []
    block: list[str] = []
    block_start = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            if not block:
                block_start = line_no
            block.append(line)
        elif block:
            segments.append(Segment("\n".join(block), locators.lines(block_start, line_no - 1)))
            block = []
    if block:
        segments.append(Segment("\n".join(block), locators.lines(block_start, block_start + len(block) - 1)))
    return ParsedDocument(ext="txt", segments=segments)
