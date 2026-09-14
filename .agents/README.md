# UniAdapt AI — Antigravity Workflow

This `.agents/` directory implements a human-gated, two-agent workflow that carries
UniAdapt AI from its SRS document through shipped, reviewed PRs — one
[SRS Section 43](../SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md#43-project-phase-mapping)
phase at a time.

It exists because the SRS is large (1527 lines, 48 sections) and the project has two
exact algorithms (Mastery Score, Adaptive Study Planner) that must be implemented
precisely, not approximated. This workflow keeps every phase's scope traceable back
to specific requirement IDs, and keeps a human in the loop at every risky step —
nothing here plans, implements, verifies, or ships without you explicitly saying so
in the conversation.

This is the Antigravity CLI/IDE counterpart of the `.claude/` workflow in this repo.
Both directories implement the same two-agent process; use whichever one matches
the tool you're running (Claude Code vs. Antigravity). Keep them in sync when
editing either one.

## Contents

```
.agents/
├── agents/
│   ├── phase-planner-implementer/
│   │   └── agent.md                          Agent 1: plans + implements a phase
│   └── implementation-verifier-shipper/
│       └── agent.md                          Agent 2: verifies + reviews + ships
├── skills/
│   ├── srs-lookup/
│   │   ├── SKILL.md                          Fast SRS lookups by ID/section/phase
│   │   └── scripts/lookup.sh
│   ├── phase-status/
│   │   ├── SKILL.md                          Reports phase progress vs. real repo state
│   │   └── scripts/check.py
│   ├── update-agents-md/
│   │   ├── SKILL.md                          Regenerates root AGENTS.md status table
│   │   └── scripts/generate.py
│   └── verify-live/
│       ├── SKILL.md                          Static SRS-ID trace + live-site check for shipped phases
│       └── scripts/audit_phases.py
├── hooks/
│   └── block-publish.sh                      PreToolUse hook script for push/PR confirmation
├── hooks.json                                 Lifecycle hooks configuration
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
        ├── plan.md                           Agent 1's saved plan for phase N
        └── verification-report.md            Agent 2's report for phase N
```

## The two agents

### Agent 1 — `phase-planner-implementer`

Plans, then (once approved) implements, the next phase.

1. Reads `docs/phase-state.json` to find the next phase (`not_started`, or
   `planned` waiting on approval, or `plan_approved` waiting on implementation).
2. Pulls only the SRS sections it needs via the `srs-lookup` skill — it does not
   read the whole document every run.
3. Cross-checks the codebase against what `phase-state.json` claims is already
   done, and flags any mismatch instead of trusting the file blindly.
4. Writes `docs/phases/phase-<N>-<name>/plan.md`, sets that phase's status to
   `"planned"`, and **stops** — no code is written yet.
5. Only when re-invoked after the phase is marked `"plan_approved"` does it
   actually implement the plan, following the SRS's fixed tech stack (Section 5)
   and, where relevant, its exact Mastery/Engagement/Planner formulas
   (Sections 23–25) byte-for-byte.
6. After implementing, runs the `update-agents-md` skill so the root
   `AGENTS.md` reflects the new phase status, then stops.
7. Never runs `git push` or `gh pr` — that's out of scope by instruction, and
   backed by a `PreToolUse` hook (see below) as a shell-level backstop.

### Agent 2 — `implementation-verifier-shipper`

Verifies a phase Agent 1 marked `"implemented"`, then ships it.

1. Re-checks the implementation against the exact FR-*/BUS-*/AC-* IDs recorded
   in that phase's `plan.md`, including negative test scenarios and (for phases
   6–7) a line-by-line diff of the algorithm math against the SRS. Uses the
   `verify-live` skill's static trace to cross-check those same IDs against
   actual repo code.
2. Runs the full existing test suite to catch regressions in earlier phases —
   `verify-live` run with no argument covers every phase currently claimed
   `implemented`/`verifying`/`verified`/`blocked`/`shipped`, not just the one
   under review, so it doubles as the regression check across all prior phases.
3. Delegates a five-axis code review (correctness, readability, architecture,
   security, performance) to a code-reviewer subagent — it doesn't reinvent
   that checklist itself.
4. Writes `docs/phases/phase-<N>-<name>/verification-report.md` with a verdict
   of `PASS` or `BLOCKED`, and **stops**.
5. Only on a fresh go-ahead does it proceed to ship: branch, commit (with the
   required attribution footer), push, open a PR via `gh`.
6. Has file-edit access restricted by instruction to only
   `docs/phase-state.json` and the phase's own `plan.md`/`verification-report.md`
   — never application code. If it finds a defect, it reports it and stops
   rather than patching it itself, so its verification signal stays honest.

## The skills

### `srs-lookup`

Looks up one thing in the SRS without loading the whole document:

```bash
bash .agents/skills/srs-lookup/scripts/lookup.sh FR-AUTH-001   # a requirement, business rule, or AC by ID
bash .agents/skills/srs-lookup/scripts/lookup.sh 23            # a whole numbered section (e.g. Mastery Score)
bash .agents/skills/srs-lookup/scripts/lookup.sh "phase 1"     # Section 43's row for a given phase
```

Both agents preload this skill and use it instead of re-reading the SRS file
directly. You can also invoke it yourself for a quick reference.

### `phase-status`

Reports current phase progress and flags disagreement between
`docs/phase-state.json` and what's actually in the repo:

```bash
python .agents/skills/phase-status/scripts/check.py
```

A `MISMATCH` line means the tracking file claims more progress than the repo
shows — investigate before trusting it further. This is a heuristic (a small
per-phase keyword map), not a substitute for reading the code.

### `update-agents-md`

Regenerates the repo-root `AGENTS.md`'s phase-status table from
`docs/phase-state.json`:

```bash
python .agents/skills/update-agents-md/scripts/generate.py
```

`phase-planner-implementer` calls this automatically at the end of its
implement step, so `AGENTS.md` stays current with real progress without
anyone needing to remember to update it by hand. It only rewrites the content
between `<!-- BEGIN AUTO-GENERATED PHASE STATUS -->` /
`<!-- END AUTO-GENERATED PHASE STATUS -->` markers in `AGENTS.md` — any
hand-written content elsewhere in the file (notes, conventions, anything a
human adds) is preserved untouched across regenerations.

### `verify-live`

Cross-checks phases already marked `implemented`/`verified`/`shipped` against
the SRS and the real repo — a static trace plus (once an app exists) a
live-site Playwright/`chromium-cli` pass:

```bash
python .agents/skills/verify-live/scripts/audit_phases.py      # every claimed-done phase
python .agents/skills/verify-live/scripts/audit_phases.py 1    # force-audit just phase 1
```

`implementation-verifier-shipper` uses this skill in its own Steps 2–3 (SRS
trace + regression check across all prior phases, not just the one under
review). A `MISSING` requirement ID is a prompt to go read that code
yourself, not proof the feature is unbuilt — see the skill's own `SKILL.md`
for the full caveats. The live-site half of the skill is unverified until the
first phase actually ships an app to point at. Unlike the other two skills,
this one is referenced by name in the agent's prompt rather than a structured
`skills:` frontmatter field — this repo's `.agents/*/agent.md` files use only
`name` and `description` in frontmatter (see "Design notes" below).

## The hook

`.agents/hooks.json` registers a `PreToolUse` hook on `run_command`, calling
`.agents/hooks/block-publish.sh` (and its Python equivalent,
`.agents/hooks/block_publish.py`). It detects `git push` and `gh pr` commands
and requests explicit confirmation via `"decision": "ask"`.

Unlike `.claude`'s equivalent hook, this one is **not** scoped to a specific
agent: the documented Antigravity `PreToolUse` hook payload
(`conversationId`, `workspacePaths`, `transcriptPath`, `artifactDirectoryPath`,
`modelName`) does not expose which agent is currently running, so there is no
confirmed way to restrict enforcement to `phase-planner-implementer` only.
Both agents (and the main session) get an `"ask"` prompt on any `git push` /
`gh pr` command; `implementation-verifier-shipper`'s Step 7 (Ship) still works
because "ask" pauses for a human decision rather than blocking outright.

## How to actually use this, end to end

Everything below happens by you typing plain requests in the main Antigravity
session — you never invoke the agents or skills directly by name unless you
want to.

1. **`"plan phase 1"`** (or "what's the next phase" / "start the next phase")
   → the main session invokes `phase-planner-implementer`, which writes
   `docs/phases/phase-1-foundation/plan.md` and stops.
2. **You review `plan.md`.** It lists the exact requirement IDs in scope, files
   to be created/changed, migrations, and a test plan.
3. **`"go ahead"` / `"approved"`** → the main session re-invokes
   `phase-planner-implementer` to implement the approved plan. It stops again
   once done.
4. **`"verify it"`** → the main session invokes `implementation-verifier-shipper`,
   which writes `verification-report.md` with a PASS/BLOCKED verdict and stops.
5. **If BLOCKED**: you decide whether to send it back to Agent 1 or fix it
   yourself, then repeat from step 3.
   **If PASS** and you say **`"ship it"`** → the main session re-invokes
   `implementation-verifier-shipper` one more time to branch, commit, push, and
   open the PR (confirming the `"ask"` prompt from the publish hook when it
   appears).
6. Repeat from step 1 for the next phase.

At every arrow above, the workflow stops and waits for you — nothing chains
automatically. `docs/phase-state.json`'s `status` field always tells you exactly
where things stand if you lose track: `not_started → planned → plan_approved →
implementing → implemented → verifying → verified/blocked → shipped`.

## Design notes for anyone modifying this workflow

- Subagents cannot pause for interactive input mid-run. Every approval gate
  here is therefore structural: the subagent writes its output and stops; the
  **main session** is what actually asks you and gets your answer, then
  re-invokes the subagent for the next step.
- Custom agent frontmatter here is kept to just `name` and `description`. The
  official Antigravity CLI docs (`/docs/cli/commands/agents`) only confirm
  those two fields for workspace agent definitions; a broader schema
  (`tools`, `model`, `commandExecutionPolicy`, `mcpServers`, `skills`,
  `plugins`, etc.) appears on the general subagents doc but is not confirmed
  for the CLI specifically, so it is deliberately left out here rather than
  guessed at.
- The publish-block hook cannot be scoped to a single agent the way
  `.claude`'s can (see "The hook" above) — this is a real capability gap
  versus `.claude`, not an oversight.
- `jq` is not assumed to be installed; scripts here use `python` for JSON
  parsing instead.
