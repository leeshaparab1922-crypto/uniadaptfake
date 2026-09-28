# ADR-0002: Unit weight sum-to-100 enforced in the service layer

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 (subjects/units), Phase 2 (curriculum)
- **SRS refs:** FR-ADM-003 (Subject/Unit catalogue)

## Context
Postgres cannot express "the sum of sibling rows equals 100" as a simple CHECK.
A trigger could, but triggers are hidden logic that students maintaining the
code rarely look for, and they do not port across databases.

## Decision
- Database: per-row `CHECK (weightage BETWEEN 0 AND 100)`.
- Service (`subject_service`): every create, update, or delete of a Subject's
  Units runs in one transaction that first locks the parent Subject row
  (`SELECT ... FOR UPDATE`), applies the change, then asserts that the Subject's
  Unit weights sum to exactly 100. Otherwise it rolls back with a validation
  error.
- Units are changed only through this service. No other code path writes the
  `units` table directly.
- Unit tests cover a sum below 100, above 100, exactly 100, and concurrent edits.

## Consequences
- Readable Python instead of a trigger, and database-portable.
- Any future code (for example Phase 2 imports) that writes Units must call
  this service.
