# Architecture Decision Records (ADRs)

Binding project decisions that the SRS leaves open. Every agent toolchain
(`.claude/`, `.agents/`, `.github/` Copilot) reads this index before planning,
implementing, or verifying a phase. An implementation that contradicts an
**Accepted** ADR is a blocking verification finding.

Rules:
- One decision per file: `ADR-NNNN-kebab-title.md`, numbered sequentially.
- ADRs never override the SRS. If the SRS later settles the question, the SRS
  wins and the ADR is marked `Superseded`.
- Never edit an Accepted ADR's decision in place. To change it, write a new ADR
  that supersedes it and set the old one's status to `Superseded by ADR-NNNN`.
- New ADRs require explicit human approval. Agents may propose them in a plan's
  "Risks & Open Questions" section but must not mark them Accepted themselves.

| ADR | Title | Status | Affects phases |
|---|---|---|---|
| [0001](ADR-0001-jwt-in-httponly-cookie.md) | JWT carried in httpOnly cookie + CSRF token | Accepted | 1, all later UI/API |
| [0002](ADR-0002-unit-weight-sum-service-layer.md) | Unit weight sum-to-100 checked in service layer | Accepted | 1, 2 |
| [0003](ADR-0003-single-subject-owner-with-audit.md) | One Subject Owner row per Subject; history via audit_logs | Accepted | 1, 2, 3 |
| [0004](ADR-0004-student-preference-deferred.md) | StudentPreference entity deferred to Phase 7 | Accepted | 1, 7 |
| [0005](ADR-0005-csv-import-row-level.md) | CSV student import is row-level atomic | Accepted | 1 |
| [0006](ADR-0006-redis-fixed-window-rate-limit.md) | Redis fixed-window rate limiting, limits in config | Accepted | 1, 8, any abuse-sensitive endpoint |
| [0007](ADR-0007-timetable-slot-types.md) | Timetable slot types: CLASS and LAB only | Accepted | 1, 7 |
| [0008](ADR-0008-phase-status-exclusions.md) | phase-status skill ignores agent-tooling folders | Accepted | tooling |
| [0009](ADR-0009-enums-as-varchar-check.md) | Enum columns stored as VARCHAR + CHECK, not native Postgres ENUM | Accepted | 1, all later migrations |
| [0010](ADR-0010-supporting-libraries-vite-dotenv-pyjwt.md) | Allow Vite, python-dotenv, and PyJWT as supporting libraries | Accepted | 1, all later phases |
| [0011](ADR-0011-audit-every-admin-mutation.md) | Every Admin create/update/delete writes an audit_logs row | Accepted | 1, all later phases |
| [0012](ADR-0012-admin-only-password-reset.md) | Password reset issued by Admin only (no self-service) | Accepted | 1 |
