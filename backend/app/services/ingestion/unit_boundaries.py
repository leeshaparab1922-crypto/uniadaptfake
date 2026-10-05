"""Unit assignment for chunks (plan P-6, FR-CON-002 "without crossing known Unit
boundaries").

- A Teacher-selected Unit applies to the whole file.
- Otherwise (syllabus, or an "all units" upload) a deterministic heading regex
  (`Unit 3`, `Module IV`, ...) switches the current Unit. The Nth heading
  number maps to the Subject's Nth Unit by order. Text before the first
  matched heading gets `unit_no = None` (reported, never guessed).
- A heading is a line whose number is followed by nothing, a separator
  (`:`, `-`, `–`, `.`, `)`), or a title starting with a capital letter or `(`.
  A wrapped sentence such as "Unit 2 covers the remaining topics" is not a
  heading (finding m2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.ingestion.parsers.base import Segment

HEADING_RE = re.compile(r"^\s*(?:unit|module)\s*[-:–.]?\s*(\d+|[ivxlc]+)\b(.*)$", re.IGNORECASE)
_SEPARATOR_START = re.compile(r"^\s*[-:–.)]")
MAX_HEADING_LINE = 100
_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


@dataclass(frozen=True)
class UnitRef:
    unit_no: int  # `Unit.order_index`
    name: str = ""


@dataclass(frozen=True)
class Block:
    text: str
    locator: str
    page_no: int | None
    unit_no: int | None


@dataclass(frozen=True)
class UnitReport:
    headings_matched: int
    ignored_headings: int
    unresolved_blocks: int


def roman_to_int(value: str) -> int | None:
    value = value.lower()
    if not value or any(ch not in _ROMAN for ch in value):
        return None
    total = 0
    for i, ch in enumerate(value):
        v = _ROMAN[ch]
        total += -v if i + 1 < len(value) and _ROMAN[value[i + 1]] > v else v
    return total


def heading_number(line: str) -> int | None:
    if len(line) > MAX_HEADING_LINE:
        return None
    m = HEADING_RE.match(line)
    if not m:
        return None
    rest = m.group(2).strip()
    if rest and not _SEPARATOR_START.match(rest) and not (rest[0].isupper() or rest[0] == "("):
        return None  # prose such as "Unit 2 covers ...", not a heading
    token = m.group(1)
    return int(token) if token.isdigit() else roman_to_int(token)


def _flush(blocks: list[Block], buf: list[str], seg: Segment, unit_no: int | None) -> None:
    text = "\n".join(buf).strip()
    if text:
        blocks.append(Block(text, seg.locator, seg.page_no, unit_no))


def assign_units(
    segments: list[Segment],
    *,
    units: list[UnitRef],
    fixed_unit_no: int | None = None,
) -> tuple[list[Block], UnitReport]:
    ordered = sorted(units, key=lambda u: u.unit_no)
    if fixed_unit_no is not None:
        fixed = [Block(s.text, s.locator, s.page_no, fixed_unit_no) for s in segments if s.text.strip()]
        return fixed, UnitReport(0, 0, 0)

    blocks: list[Block] = []
    current: int | None = None
    matched = ignored = 0
    for seg in segments:
        buf: list[str] = []
        buf_unit = current
        for line in seg.text.split("\n"):
            n = heading_number(line)
            if n is not None:
                if 1 <= n <= len(ordered):
                    _flush(blocks, buf, seg, buf_unit)
                    buf = []
                    current = ordered[n - 1].unit_no
                    buf_unit = current
                    matched += 1
                else:
                    ignored += 1
            buf.append(line)
        _flush(blocks, buf, seg, buf_unit)
    unresolved = sum(1 for b in blocks if b.unit_no is None)
    return blocks, UnitReport(matched, ignored, unresolved)
