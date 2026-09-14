---
name: srs-lookup
description: Look up SRS sections, FR-/BUS-/AC-/OBJ-/BR-/NFR-/US-IDs, or Section-43 phase rows by ID, section number, or phase number, without reading the full 1527-line SRS document.
---

# SRS Lookup

Use this skill instead of reading the whole SRS document whenever you need a specific requirement, business rule, acceptance criterion, or phase row. The SRS is large (~1527 lines / ~86k tokens); targeted lookups keep context usage proportional to what's actually needed.

Run:

```bash
bash scripts/lookup.sh <QUERY>
```

Query forms:
- An ID such as `FR-AUTH-001`, `BUS-014`, `AC-010`, `OBJ-001`, `BR-005`, `NFR-SEC-004`, `US-ADM-001` — prints the matching table row(s)/line(s) referencing that ID.
- A bare section number, e.g. `43` or `23` — prints that entire numbered section (`## 43. ...`) through (not including) the next numbered section heading.
- `phase N` or `phase-N` (e.g. `phase 1`) — prints Section 43's table row for that phase number (Main Features / Requirements / Dependencies / Expected Demo).

If a query returns nothing, double-check the exact ID spelling against Section 12 (Functional Requirements), Section 11 (Business Rules), or Section 40 (Acceptance Criteria) headings rather than guessing at a different ID.

For a phase's full requirement set, first look up `phase N` to get the FR-ID ranges in scope, then look up each individual FR-ID.
