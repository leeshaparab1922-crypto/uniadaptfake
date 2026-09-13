# UniAdapt AI — Claude Code Workflow

This `.claude/` directory implements a human-gated, two-agent workflow that carries
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
.claude/
├── agents/
│   ├── phase-planner-implementer.md      Agent 1: plans + implements a phase
│   └── implementation-verifier-shipper.md Agent 2: verifies + reviews + ships
├── skills/
│   ├── srs-lookup/                        Fast SRS lookups by ID/section/phase
│   ├── phase-status/                      Reports phase progress vs. real repo state
│   └── update-claude-md/                  Regenerates root CLAUDE.md's status table
├── hooks/
│   └── block-agent1-publish.sh            Blocks Agent 1 from git push / gh pr
├── settings.json                          Wires the hook above into PreToolUse
└── README.md                              This file
```

Related, outside `.claude/` but part of the same workflow:

```
CLAUDE.md                                  Auto-updated project + phase status (repo root)
docs/
├── phase-state.json                       Single source of truth: phase progress
├── templates/
│   ├── phase-plan-template.md
│   └── verification-report-template.md
└── phases/
    └── phase-<N>-<name>/
        ├── plan.md                        Agent 1's saved plan for phase N
        └── verification-report.md         Agent 2's report for phase N
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
6. After implementing, runs the `update-claude-md` skill so the root
   `CLAUDE.md` reflects the new phase status, then stops.
7. Never runs `git push` or `gh pr` — that's enforced by a hook (see below), not
   just a suggestion in its prompt.

### Agent 2 — `implementation-verifier-shipper`

Verifies a phase Agent 1 marked `"implemented"`, then ships it.

1. Re-checks the implementation against the exact FR-*/BUS-*/AC-* IDs recorded
   in that phase's `plan.md`, including negative test scenarios and (for phases
   6–7) a line-by-line diff of the algorithm math against the SRS.
2. Runs the full existing test suite to catch regressions in earlier phases.
3. Delegates a five-axis code review (correctness, readability, architecture,
   security, performance) to the existing `agent-skills:code-reviewer` agent —
   it doesn't reinvent that checklist itself.
4. Writes `docs/phases/phase-<N>-<name>/verification-report.md` with a verdict
   of `PASS` or `BLOCKED`, and **stops**.
5. Only on a fresh go-ahead does it proceed to ship: branch, commit (with the
   required attribution footer), push, open a PR via `gh`.
6. Has `Edit` access restricted by instruction to only
   `docs/phase-state.json` and the phase's own `plan.md`/`verification-report.md`
   — never application code. If it finds a defect, it reports it and stops
   rather than patching it itself, so its verification signal stays honest.

## The three skills

### `srs-lookup`

Looks up one thing in the SRS without loading the whole document:

```bash
.claude/skills/srs-lookup/lookup.sh FR-AUTH-001   # a requirement, business rule, or AC by ID
.claude/skills/srs-lookup/lookup.sh 23            # a whole numbered section (e.g. Mastery Score)
.claude/skills/srs-lookup/lookup.sh "phase 1"     # Section 43's row for a given phase
```

Both agents preload this skill and use it instead of re-reading the SRS file
directly. You can also invoke it yourself for a quick reference.

### `phase-status`

Reports current phase progress and flags disagreement between
`docs/phase-state.json` and what's actually in the repo:

```bash
python .claude/skills/phase-status/check.py
```

A `MISMATCH` line means the tracking file claims more progress than the repo
shows — investigate before trusting it further. This is a heuristic (a small
per-phase keyword map), not a substitute for reading the code.

### `update-claude-md`

Regenerates the repo-root `CLAUDE.md`'s phase-status table from
`docs/phase-state.json`:

```bash
python .claude/skills/update-claude-md/generate.py
```

`phase-planner-implementer` calls this automatically at the end of its
implement step, so `CLAUDE.md` stays current with real progress without
anyone needing to remember to update it by hand. It only rewrites the content
between `<!-- BEGIN AUTO-GENERATED PHASE STATUS -->` /
`<!-- END AUTO-GENERATED PHASE STATUS -->` markers in `CLAUDE.md` — any
hand-written content elsewhere in the file (notes, conventions, anything a
human adds) is preserved untouched across regenerations.

## The hook

`.claude/hooks/block-agent1-publish.sh`, wired via `.claude/settings.json`'s
`PreToolUse` hook on the `Bash` tool, blocks `git push` and `gh pr` **only when
the invoking agent is `phase-planner-implementer`**. The main session and
`implementation-verifier-shipper` are unaffected. This is a backstop — Agent 1
is also instructed never to run these commands — enforced at the shell level so
it can't be talked around.

## How to actually use this, end to end

Everything below happens by you typing plain requests in the main Claude Code
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
   open the PR.
6. Repeat from step 1 for the next phase.

At every arrow above, the workflow stops and waits for you — nothing chains
automatically. `docs/phase-state.json`'s `status` field always tells you exactly
where things stand if you lose track: `not_started → planned → plan_approved →
implementing → implemented → verifying → verified/blocked → shipped`.

## Design notes for anyone modifying this workflow

- Subagents cannot pause for interactive input mid-run (no `AskUserQuestion`
  inside a subagent). Every approval gate here is therefore structural: the
  subagent writes its output and stops; the **main session** is what actually
  asks you and gets your answer, then re-invokes the subagent for the next step.
- The `Agent(agent-name)` frontmatter syntax that scopes which subagents an
  agent may spawn **only works when that agent is running as the main session**
  (`claude --agent`). A subagent like `implementation-verifier-shipper` cannot
  be scoped that way in its own frontmatter — its restriction to only invoking
  `agent-skills:code-reviewer` is enforced by instruction in its prompt, not by
  the tool system. Keep this in mind if you add more delegated subagents.
- `disallowedTools` entries with command patterns (e.g. `Bash(git push *)`)
  remove the **entire** tool, not just matching commands — that's why the
  publish restriction here is a `PreToolUse` hook keyed on `agent_type`, not a
  frontmatter denylist.
- `jq` is not assumed to be installed; scripts here use `python` for JSON
  parsing instead.
