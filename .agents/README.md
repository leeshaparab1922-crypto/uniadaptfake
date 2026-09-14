# UniAdapt AI — Antigravity Workflow

This `.agents/` directory implements a human-gated, two-agent Antigravity workflow that carries
UniAdapt AI from its SRS document through shipped, reviewed PRs — one
[SRS Section 43](../SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md#43-project-phase-mapping)
phase at a time.

It exists because the SRS is large (1527 lines, 48 sections) and the project has two
exact algorithms (Mastery Score, Adaptive Study Planner) that must be implemented
precisely, not approximated. This workflow keeps every phase's scope traceable back
to specific requirement IDs, and keeps a human in the loop at every risky step —
nothing here plans, implements, verifies, or ships without you explicitly saying so
in the conversation.

## Contents

```
.agents/
├── skills/
│   ├── phase-planner-implementer/
│   │   └── SKILL.md                          Phase planner + implementer skill
│   ├── implementation-verifier-shipper/
│   │   └── SKILL.md                          Phase verifier + reviewer + shipper skill
│   ├── srs-lookup/
│   │   ├── SKILL.md                          Fast SRS lookups by ID/section/phase
│   │   └── scripts/lookup.sh
│   ├── phase-status/
│   │   ├── SKILL.md                          Reports phase progress vs. real repo state
│   │   └── scripts/check.py
│   └── update-agents-md/
│       ├── SKILL.md                          Regenerates root AGENTS.md status table
│       └── scripts/generate.py
├── hooks/
│   └── block-publish.sh                      PreToolUse hook script for push/PR confirmation
├── hooks.json                                Lifecycle hooks configuration
└── README.md                                  This file
```

Related, outside `.agents/` but part of the same workflow:

```
AGENTS.md                                     Auto-updated project + phase status (repo root)
docs/
├── phase-state.json                          Single source of truth: phase progress
├── templates/
│   ├── phase-plan-template.md
│   └── verification-report-template.md
└── phases/
    └── phase-<N>-<name>/
        ├── plan.md                           Saved plan for phase N
        └── verification-report.md            Saved verification report for phase N
```

## The Workflow Skills

### 1. `phase-planner-implementer`
Plans, then (once approved) implements, the next phase.

1. Reads `docs/phase-state.json` to find the next phase (`not_started`, `planned`, or `plan_approved`).
2. Pulls SRS requirement sections via `srs-lookup`.
3. Checks existing codebase state with `phase-status`.
4. Writes `docs/phases/phase-<N>-<name>/plan.md` and sets status to `"planned"`, then stops for approval.
5. Implements code only after status is `"plan_approved"`.
6. Runs `update-agents-md` skill to keep `AGENTS.md` up to date.

### 2. `implementation-verifier-shipper`
Verifies a phase marked `"implemented"`, then ships it.

1. Re-checks implementation against requirement IDs in `plan.md`.
2. Runs test suite for regression testing.
3. Performs 5-axis code review.
4. Writes `docs/phases/phase-<N>-<name>/verification-report.md`.
5. Branches, commits, pushes, and opens PR via `gh` after human confirmation.

### 3. Utility Skills
- `srs-lookup`: Fast targeted lookup of requirement IDs (FR-*/BUS-*/AC-*), section numbers, or phase rows.
- `phase-status`: Reports progress and flags state file / repo mismatches.
- `update-agents-md`: Automatically updates the status table in `AGENTS.md`.

## Lifecycle Hook
`hooks.json` registers a `PreToolUse` hook on `run_command` calling `./hooks/block-publish.sh`.
It detects `git push` and `gh pr` commands and requests explicit confirmation via `"decision": "ask"`.
