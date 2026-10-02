# ADR-0011: Every Admin create/update/delete writes an audit_logs row

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 and every later phase that adds Admin (or other privileged) mutations
- **SRS refs:** FR-ADM-006 Post ("Allocation is audited"), FR-ADM-001..007, NFR-SEC audit-trail requirements (Section 36)

## Context
Phase 1 verification was BLOCKED because enrollment and elective allocation wrote
no audit record, and the same gap existed across the other Admin requirements.
Without a single rule, each requirement's author decides separately and gaps
appear.

## Decision
- Every service function that creates, updates, deactivates, or deletes data on
  an Admin's behalf writes an `audit_logs` row **in the same transaction**,
  recording actor, action, entity type/id, before/after (where applicable), and
  reason (where supplied).
- Service functions that mutate data take the acting user as an explicit
  parameter. Routes always pass `current_user`.
- One shared helper (for example `app/services/audit.py::record(...)`) is used.
  No hand-built audit rows.
- Bulk operations (CSV import, promotion/transfer) write one audit row per
  created or changed record, or one row per operation that references an
  operation id resolvable to every affected record.
- Tests assert that the audit row exists for each mutating service function.

## Consequences
- A mutating Admin path without an audit row is a blocking verification finding.
- Later phases apply the same rule to Teacher/Owner approvals and other
  privileged changes unless a new ADR says otherwise.
