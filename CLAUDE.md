# UniAdapt AI

UniAdapt AI is a department-wise adaptive learning platform for one engineering
college, connecting academic structure, approved course content, actual
classroom coverage, diagnostic evidence, and student availability to produce
explainable daily/weekly study plans. Three roles only: Admin, Teacher, Student.

Full requirements: [`SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md`](SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md)
(48 sections — use the `srs-lookup` skill for targeted lookups rather than
reading it end to end).

Implementation proceeds one SRS Section-43 phase at a time via a two-agent
Claude Code workflow (`phase-planner-implementer` plans/implements,
`implementation-verifier-shipper` verifies/reviews/ships), always gated on
explicit human approval between steps. Full workflow docs:
[`.claude/README.md`](.claude/README.md).

The status table below is auto-generated from `docs/phase-state.json` by the
`update-claude-md` skill, run by `phase-planner-implementer` after it finishes
implementing each phase. Do not hand-edit the block between the markers —
edits there are overwritten on the next regeneration. Anything outside the
markers (including this section) is preserved as-is.

<!-- BEGIN AUTO-GENERATED PHASE STATUS (update-claude-md skill) -->

_Last regenerated: 2026-09-28T08:07:57_

**Current phase:** 1 — Foundation (Verified (ready to ship))

| Phase | Name | Status | SRS Requirements | Dependencies | Plan | Verification | PR |
|---|---|---|---|---|---|---|---|
| 1 | Foundation | Verified (ready to ship) | FR-AUTH-001..004, FR-ADM-001..007, FR-STU-001 | None | [plan](docs/phases/phase-1-foundation/plan.md) | [report](docs/phases/phase-1-foundation/verification-report.md) | - |
| 2 | Ingestion & Curriculum | Not started | FR-CON-001..004, FR-CUR-001..004 | Phase 1 SubjectInstances/Teachers | - | - | - |
| 3 | Assessment & Bank | Not started | FR-QB-001..005 | Phase 2 active Topics/content | - | - | - |
| 4 | Coverage Tracker & Diagnostics | Not started | FR-COV-001..004, FR-DIA-001..006, FR-ADM-008, FR-STU-003 | Phase 3 READY bank | - | - | - |
| 5 | Grading | Not started | FR-GRD-001..007, FR-STU-006 | Phase 4 attempts, Phase 3 grading artifacts | - | - | - |
| 6 | Learner Model | Not started | FR-TCH-003, FR-LRN-001..005 | Phase 5 valid evidence, Phase 1 rosters | - | - | - |
| 7 | Planner | Not started | FR-PLN-001..008, FR-TCH-002, FR-STU-002..004 | Phase 6 mastery, Phase 1 exam/timetable/preferences, Phase 4 coverage | - | - | - |
| 8 | Daily Learning, Quiz & Tutor | Not started | FR-DAY-001, FR-TUT-001..003, FR-PRC-001..003 | Phase 2, Phase 3, Phase 5, Phase 6, Phase 7 | - | - | - |
| 9 | Recommendation, Intervention, Notifications & Reports | Not started | FR-REC-001, FR-INT-001..002, FR-NOT-001, FR-RPT-001..003, FR-ADM-009 | All core phases | - | - | - |

Full workflow details: [`.claude/README.md`](.claude/README.md). Raw tracking data: [`docs/phase-state.json`](docs/phase-state.json). Full spec: [`SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md`](SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md).

<!-- END AUTO-GENERATED PHASE STATUS (update-claude-md skill) -->
