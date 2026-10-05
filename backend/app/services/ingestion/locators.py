"""Source locators (ADR-0014, FR-CON-003): `page:7`, `slide:3`, `slide:3#notes`,
`section:Unit 2 > Trees#p14`, `lines:40-95`. Mandatory: never null/empty."""

from __future__ import annotations

import re

from app.core.errors import ValidationError

PAGE, SLIDE, SECTION, LINES = "PAGE", "SLIDE", "SECTION", "LINES"
_RANGE = re.compile(r"^(page|slide|lines):(\d+)(?:-(\d+))?(#notes)?$")


def page(n: int) -> str:
    return f"page:{n}"


def slide(n: int, *, notes: bool = False) -> str:
    return f"slide:{n}#notes" if notes else f"slide:{n}"


def section(heading_path: list[str], paragraph_index: int) -> str:
    path = " > ".join(h.strip() for h in heading_path if h.strip()) or "(document)"
    return f"section:{path}#p{paragraph_index}"


def lines(start: int, end: int) -> str:
    if end < start:
        start, end = end, start
    return f"lines:{start}-{end}"


def validate(locator: str | None) -> str:
    if locator is None or not locator.strip():
        raise ValidationError("A source locator is required for every chunk.")
    value = locator.strip()
    prefix, _, rest = value.partition(":")
    if prefix not in {"page", "slide", "section", "lines"} or not rest:
        raise ValidationError(f"Invalid locator: {value!r}")
    return value


def locator_type(locator: str) -> str:
    prefix = validate(locator).split(":", 1)[0]
    return {"page": PAGE, "slide": SLIDE, "section": SECTION, "lines": LINES}[prefix]


def page_no_of(locator: str) -> int | None:
    """Page (or slide) number of the first page/slide in a locator; None for sections/lines."""
    m = _RANGE.match(validate(locator))
    if m and m.group(1) in ("page", "slide"):
        return int(m.group(2))
    return None


def merge(first: str, last: str) -> str:
    """Locator spanning two segments of the same kind (a chunk crossing pages/slides/lines)."""
    a, b = _RANGE.match(first), _RANGE.match(last)
    if a and b and a.group(1) == b.group(1) and not a.group(4) and not b.group(4):
        lo = min(int(a.group(2)), int(b.group(2)))
        hi = max(int(a.group(3) or a.group(2)), int(b.group(3) or b.group(2)))
        return f"{a.group(1)}:{lo}" if lo == hi else f"{a.group(1)}:{lo}-{hi}"
    return first
