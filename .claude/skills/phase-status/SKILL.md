---
name: phase-status
description: Report the current UniAdapt AI phase, its status, and whether repo contents actually match docs/phase-state.json (catches a stale or hand-edited state file).
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/check.py *)
shell: bash
---

# Phase Status

Use this skill before planning or implementing any phase, to find out which SRS Section-43 phase is next and to confirm the tracking file agrees with what is actually in the repo.

Run:

```bash
python ${CLAUDE_SKILL_DIR}/check.py
```

This reads `docs/phase-state.json` and prints, per phase: its recorded status, and a best-effort check for whether that phase's expected deliverables exist anywhere in the repo. A `MISMATCH` line means the state file claims more progress than the repo shows — treat this as a signal to investigate before trusting the state file, not something to silently overwrite.

This check is a heuristic (a small hardcoded map of expected directory/file name fragments per phase), not a substitute for actually reading the relevant code when a phase is claimed complete. Use it to decide where to look next, not as the final verification.
