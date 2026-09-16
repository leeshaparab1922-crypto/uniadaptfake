---
name: srs-lookup
description: "Look up SRS sections, FR-/BUS-/AC-/OBJ-/BR-/NFR-/US-IDs, or Section-43 phase rows by ID, section number, or phase number, without reading the full 1527-line SRS document."
---

# SRS Lookup

Use this skill instead of reading the whole SRS document whenever you need a specific requirement, business rule, acceptance criterion, or phase row. The SRS is large (~1527 lines / ~86k tokens); targeted lookups keep context usage proportional to what's actually needed.

Run:

```bash
bash lookup.sh "phase 1"
```

Query forms:
- An ID such as `FR-AUTH-001`, `BUS-014`, `AC-010`, `OBJ-001`, `BR-005`, `NFR-SEC-004`, `US-ADM-001` — prints the matching table row(s)/line(s) referencing that ID.
- A bare section number, e.g. `43` or `23` — prints that entire numbered section (`## 43. ...`) through (not including) the next numbered section heading.
- `phase N` or `phase-N` (e.g. `phase 1`) — prints Section 43's table row for that phase number (Main Features / Requirements / Dependencies / Expected Demo).

If a query returns nothing, double-check the exact ID spelling against Section 12 (Functional Requirements), Section 11 (Business Rules), or Section 40 (Acceptance Criteria) headings rather than guessing at a different ID.

For a phase's full requirement set, first look up `phase N` to get the FR-ID ranges in scope, then look up each individual FR-ID.

## Copilot invocation and scope

Read this skill from `.github/skills/srs-lookup/SKILL.md` even if a same-named
skill is discovered elsewhere. Resolve the base directory from this SKILL.md's
absolute location. Run the adjacent script with its absolute quoted path, or
change directory to that base first; repository-relative examples assume the
repository root. Python scripts resolve the repo from `__file__`; the Bash script
uses `BASH_SOURCE[0]`. There are no injected skill-directory variables.
Use Python 3.11+ (`python` on Windows, `python3` on Unix if needed).
No blanket shell pre-approval is granted. Respect the current task's write scope.

On Windows without Bash, use `pwsh -NoProfile -File lookup.ps1 "phase 1"`
from this skill directory, or `python lookup.py "phase 1"`.
Pass one quoted query argument. Both adapters retain success=0, missing/invalid=1.
The source comment mentions `Section 43`, but its parser accepts only `43`;
use the supported numeric form. No arguments prints usage and exits 1.
