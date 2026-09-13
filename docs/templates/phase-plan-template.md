# Phase <N> — <Phase Name> — Implementation Plan

## Phase

- Phase number: <N>
- Phase name: <name from SRS Section 43>
- SRS Section-43 row: Main Features / Requirements / Dependencies / Expected Demo (quote verbatim)

## Requirements in Scope

List every FR-*, BUS-*, and AC-* ID this phase must satisfy, pulled via the `srs-lookup` skill (not summarized from memory). For each FR-*, include its Pre/Trigger/Input/Processing/Val/Output/Post/AC fields.

| ID | Type (FR/BUS/AC) | Summary |
|---|---|---|
| | | |

## Dependencies Check

For each dependency listed in Section 43 for this phase, state whether it is genuinely satisfied in the current codebase (not just marked "shipped" in phase-state.json) — cite the specific files/migrations/endpoints that prove it.

| Dependency | Satisfied? | Evidence |
|---|---|---|

## Files to Create

| Path | Purpose |
|---|---|

## Files to Change

| Path | Change |
|---|---|

## Migrations

Describe any Alembic migrations needed (new tables/columns/constraints), referencing the SRS Section 31 data entities involved.

## Test Plan

Map tests to the phase's Expected Demo bar (Section 43) and to the relevant AC-* Given/When/Then scenarios (Section 40) — both positive and negative paths.

## Exact-Algorithm Call-Outs

If this phase touches Sections 23 (Mastery Score), 24 (Engagement Score), or 25 (Adaptive Study Planner), state so explicitly here and note that these formulas must be implemented exactly as specified, not approximated.

## Risks & Open Questions

## Approval

- [ ] Approved by human reviewer
- Date approved:
- Notes:
