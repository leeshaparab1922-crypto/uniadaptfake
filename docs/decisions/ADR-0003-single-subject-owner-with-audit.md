# ADR-0003: One Subject Owner row per Subject; owner history via audit_logs

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 (assignments), Phases 2–3 (Owner-only approvals)
- **SRS refs:** FR-ADM-002, Section 43 Phase 1 demo bar ("one Subject Owner per Subject")

## Decision
- `subject_owner_assignments` has a unique index on `subject_id`, so the
  database enforces exactly one current owner per Subject.
- Changing the owner updates that row in place **and** writes an `audit_logs`
  entry (actor, old owner, new owner, reason, timestamp) in the same transaction.
- The owner must be an active user with role `TEACHER`.

## Consequences
- The simplest possible invariant, with full change history still available
  through the audit log.
- If a later SRS requirement needs owner history as first-class data, a new ADR
  can introduce an append-only table and backfill it from `audit_logs`.
- The SRS also mentions a "PRIMARY Subject Owner" for setting a question bank to
  READY. The Phase 3 planner must check whether that implies anything beyond
  this ADR and propose a new ADR if so.
