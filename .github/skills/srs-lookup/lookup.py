#!/usr/bin/env python3
"""Native Windows equivalent of lookup.sh; one query, exit 0/1, read-only."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
SRS = ROOT / "SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md"


def lookup(query, lines):
    if re.fullmatch(r"(FR|BUS|AC|OBJ|BR|NFR|US)-[A-Z0-9-]+", query):
        matches = [(i, line) for i, line in enumerate(lines, 1) if f"| {query} " in line]
        if not matches:
            matches = [(i, line) for i, line in enumerate(lines, 1) if query in line]
        if not matches:
            raise ValueError(f"No match found for ID: {query}")
        return [f"{i}:{line}" for i, line in matches]
    phase = re.fullmatch(r"[Pp]hase[\s_-]?([0-9]+)", query)
    section = "43" if phase else query
    if not re.fullmatch(r"[0-9]+", section):
        raise ValueError(f"Unrecognized query form: {query}")
    start = next((i for i, line in enumerate(lines) if line.startswith(f"## {section}. ")), None)
    if start is None:
        raise ValueError(f"No section heading found for number: {section}")
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^## [0-9]+\.", lines[i])), len(lines))
    result = lines[start:end]
    if phase:
        result = [line for line in result if line.startswith(f"| {phase[1]} ")]
        if not result:
            raise ValueError(f"No Section 43 row found for phase {phase[1]}")
    return result


def main():
    try:
        if not SRS.is_file():
            raise ValueError(f"ERROR: SRS file not found at {SRS}")
        query = sys.argv[1] if len(sys.argv) > 1 else ""
        if not query:
            raise ValueError("Usage: lookup.py <FR-ID|BUS-ID|AC-ID|section-number|'phase N'>")
        print("\n".join(lookup(query, SRS.read_text(encoding="utf-8").splitlines())))
        return 0
    except (ValueError, OSError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
