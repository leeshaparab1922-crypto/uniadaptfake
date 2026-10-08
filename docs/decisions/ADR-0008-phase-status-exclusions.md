# ADR-0008: phase-status skill ignores agent-tooling folders

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** workflow tooling (all three agent toolchains)

## Context
`phase-status/check.py` guesses whether a phase has deliverables by matching
file names such as `backend` or `planner`. The copies disagreed on which folders
to skip:
- `.claude/` skipped only `.claude`.
- `.agents/` skipped `.agents` and `.claude`.
- `.github/` skipped all tooling folders.

As a result, rule files such as `.agents/rules/backend.md` made the `.claude`
copy falsely report deliverables for Phases 1 and 7.

## Decision
All three copies (`.claude/`, `.agents/`, `.github/`) use the same exclusion set:
`.git`, `node_modules`, `.venv`, `__pycache__`, `.claude`, `.github`, `.agents`,
`SRS_Doc`, `docs`.

## Consequences
The heuristic looks only at application folders. Any future change to the
exclusion set must be made in all three copies.
