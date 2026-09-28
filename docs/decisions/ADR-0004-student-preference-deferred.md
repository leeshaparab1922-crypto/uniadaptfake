# ADR-0004: StudentPreference entity deferred to Phase 7

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 (not created), Phase 7 (must create it)
- **SRS refs:** Section 31.1 (StudentPreference), Section 43 Phase 7 row, FR-STU-002..004

## Decision
Phase 1's migration does **not** create a `student_preferences` table, because
no Phase 1 requirement uses it.

## Consequences
- **The Phase 7 planner must** add the `StudentPreference` table (per Section
  31.1) in its own Alembic migration and list it in its plan.
- Nothing in Phases 1–6 may depend on student availability or preferences.
