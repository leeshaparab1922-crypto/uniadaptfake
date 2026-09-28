# ADR-0005: CSV student import is row-level atomic

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 (student import); the default pattern for later bulk imports
- **SRS refs:** FR-ADM-005 ("mixed file imports valid rows and names invalid row reasons")

## Decision
- Each CSV row is its own all-or-nothing unit (one savepoint per row).
- Valid rows are created. Invalid rows create nothing and appear in a report
  with the row number and a named reason.
- The whole file is rejected only when it is structurally unreadable: wrong
  headers, bad encoding, or over the configured size or row limit.

## Consequences
Later bulk-import features follow the same pattern unless their requirement says
otherwise, in which case they need a new ADR.
