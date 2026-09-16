# UniAdapt AI — Copilot workflow

UniAdapt AI is a department-wise adaptive learning platform for one engineering
college. It connects academic structure, approved course content, classroom
coverage, diagnostic evidence and student availability to explainable daily and
weekly study plans. Exactly three roles: Admin, Teacher, Student.

`SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md` is the
authoritative requirements source. Use `.github/skills/srs-lookup/SKILL.md` for
targeted reads. Preserve SRS traceability: exact FR-/BUS-/AC- IDs, complete
Pre/Trigger/Input/Processing/Val/Output/Post/AC fields, positive and negative
acceptance scenarios, and line-by-line formula checks for Sections 23–25.
Never approximate or improve the deterministic algorithms. BUS invariants and
AI/deterministic boundary violations block acceptance.

No agent or session may edit or write anything under `SRS_Doc/`, through file
tools, shell scripts, APIs, delegated agents, or formatters. Humans amend the SRS
directly outside agent tool calls. Keep `.claude/**` untouched: it is the source
workflow, not a runtime dependency to repair or regenerate during this port.

## Human approval and phase state

Implement one Section-43 phase at a time. Read `docs/phase-state.json` and compare
its claims to real code using phase-status before planning. Dependencies must
exist and work, not merely carry a shipped label. Use the existing plan/report
templates in `docs/templates/`; save artifacts under `docs/phases/phase-N-name/`.

1. On a human planning request, use `phase-planner-implementer` to save a plan
   with exact requirements, file changes, migrations, tests, risks and dependencies.
   Set `planned`, then STOP; no implementation in that invocation.
2. After explicit human approval of that phase's saved plan, the main session
   records `plan_approved` and approval evidence. Re-invoke Agent 1 to implement.
   A status file alone does not establish approval. Deviations require a revised
   plan and approval. Finish with `implemented`, timestamp, and update-claude-md
   when root-file changes are authorized; STOP before verification.
3. After a human verification request, use `implementation-verifier-shipper`.
   Re-read SRS/plan requirements, audit static traces and actual behavior, run the
   full regression suite and relevant live checks, delegate a five-axis independent
   review, record PASS/BLOCKED and `verified`/`blocked`, then STOP.
4. Only fresh, phase-specific human shipping approval in the conversation permits
   Agent 2 to branch, commit with truthful attribution, push (never force), and
   create a PR. Confirm the reviewed changes are unchanged; otherwise reverify.
   Record the PR URL and `shipped`. Earlier plan or phase approval is insufficient.

The phase state sequence is `not_started → planned → plan_approved → implementing
→ implemented → verifying → verified/blocked → shipped`. Keep the active top-level
phase and per-phase record consistent. Record artifact paths and timestamps.
Never automatically chain stages or treat an autopilot/tool permission as approval.

Agent 1 must never execute `git push`, any `gh pr` command, PR publication,
deployment, or equivalent remote publishing through shell, MCP, API or delegation.
Agent 2 owns shipping only after approval. While verifying it may edit only
`docs/phase-state.json` and the target phase's plan/report; it must report defects
and stop, never patch application code/tests/migrations or run fixing formatters.

## Copilot resources and coexistence

The complete profiles are in `.github/agents/*.agent.md`; skills and their helper
scripts are in `.github/skills/`; path rules use `.github/instructions/*.instructions.md`.
The general rule below is included repository-wide, including planning-only turns.
Backend, frontend and deterministic-service rules also load by `applyTo` path.
Read all four explicitly when conducting a review.

@instructions/general.instructions.md

Use the Copilot profiles through `/agent` or `copilot --agent=<name>`. Prefer
`.github/copilot/agent1.ps1` (Windows) or `agent1.sh` (Unix) for a dedicated Agent 1
session with additional publication restrictions. End that session before switching
to Agent 2. Do not change, unset or bypass the launcher's restriction.

Hooks are in `.github/hooks/uniadapt.json`; payload adapters and both platform
wrappers are under `.github/hooks/scripts/`. Tool hooks do not provide reliable
agent identity. Publication is therefore a shared human-review gate, with an
additional denial in a dedicated Agent 1 session, NOT exact per-agent enforcement.
Do not approve a publication prompt on Agent 1's behalf. See `.github/README.md`
for shell/timeout limits, legacy configuration coexistence, and validation evidence.

Copilot also discovers existing `AGENTS.md`, `CLAUDE.md`, `.claude` and `.agents`
resources. They describe other runtimes of the same workflow; use the explicit
`.github` paths for this runtime. Do not edit those resources to resolve a conflict.
Inspect `/instructions` and `/skills info <name>` if discovery differs. The
update-claude-md skill retains its root `CLAUDE.md` purpose; it is not permission
to change root files during a `.github`-only task. User scope restrictions apply
to all phase helpers and validation commands.
