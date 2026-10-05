"""Cleaning (SRS Section 17): remove repeated headers/footers and extraction
noise while retaining page/source boundaries. It never rewrites academic
meaning: no de-hyphenation, no spelling or number changes, no re-wrapping."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import replace

from app.services.ingestion.parsers.base import Segment
from app.services.ingestion.unit_boundaries import HEADING_RE

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​﻿]")
_SPACES = re.compile(r"[ \t ]+")
_BLANKS = re.compile(r"\n{3,}")
_PAGE_NUMBER = re.compile(r"\b(?:page|pg|slide)\.?\s*\d+(?:\s*(?:of|/)\s*\d+)?", re.IGNORECASE)
_BARE_NUMBER = re.compile(r"^\W*\d+\W*$")
EDGE_LINES = 2  # candidate header/footer lines examined at the top/bottom of a page
MIN_LINES_FOR_TWO_EDGE_LINES = 5  # shorter pages only expose their first/last line
MIN_PAGES_FOR_HEADER_DETECTION = 3
MAX_HEADER_LENGTH = 120


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANKS.sub("\n\n", text).strip()


def _key(line: str) -> str:
    """Comparison key. Only *page-number* digits are normalised ("Page 3 of 10" == "Page 4 of 10");
    other digits are kept so "Unit 1"/"Unit 2" or numbered body lines are never conflated."""
    key = _SPACES.sub(" ", line.strip().lower())
    key = _PAGE_NUMBER.sub("page #", key)
    return "#" if _BARE_NUMBER.match(key) else key


def _edge_indices(lines: list[str]) -> set[int]:
    non_empty = [i for i, ln in enumerate(lines) if ln.strip()]
    if len(non_empty) < 3:
        return set()  # never strip a page down to nothing
    n = EDGE_LINES if len(non_empty) >= MIN_LINES_FOR_TWO_EDGE_LINES else 1
    return set(non_empty[:n] + non_empty[-n:])


def _is_paged(seg: Segment) -> bool:
    return (
        seg.locator.startswith("page:") or seg.locator.startswith("slide:")
    ) and "#notes" not in seg.locator


def _edge_keys(lines: list[str]) -> set[str]:
    return {
        _key(lines[i])
        for i in _edge_indices(lines)
        if len(lines[i]) <= MAX_HEADER_LENGTH and not HEADING_RE.match(lines[i])
    }


def remove_repeated_headers_footers(segments: list[Segment]) -> list[Segment]:
    paged = [s for s in segments if _is_paged(s) and s.text.strip()]
    if len(paged) < MIN_PAGES_FOR_HEADER_DETECTION:
        return segments
    counts: Counter[str] = Counter()
    for seg in paged:
        for key in _edge_keys(seg.text.split("\n")):
            counts[key] += 1
    threshold = max(MIN_PAGES_FOR_HEADER_DETECTION, math.ceil(len(paged) * 0.5))
    repeated = {k for k, c in counts.items() if c >= threshold}
    if not repeated:
        return segments

    result: list[Segment] = []
    for seg in segments:
        if not (_is_paged(seg) and seg.text.strip()):
            result.append(seg)
            continue
        lines = seg.text.split("\n")
        edge_idx = _edge_indices(lines)
        kept = [ln for i, ln in enumerate(lines) if not (i in edge_idx and _key(ln) in repeated)]
        result.append(replace(seg, text=normalize_text("\n".join(kept))))
    return result


def clean_segments(segments: list[Segment]) -> list[Segment]:
    """Normalise, strip repeated headers/footers; drop emptied segments. Pages
    flagged `needs_ocr` are always kept so OCR failures can name their page."""
    normalised = [replace(s, text=normalize_text(s.text)) for s in segments]
    stripped = remove_repeated_headers_footers(normalised)
    return [s for s in stripped if s.text or s.needs_ocr]
