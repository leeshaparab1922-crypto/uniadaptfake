---
name: phase-status
description: "Report the current UniAdapt AI phase, its status, and whether repo contents actually match docs/phase-state.json (catches a stale or hand-edited state file)."
---

# Phase Status

Use this skill before planning or implementing any phase, to find out which SRS Section-43 phase is next and to confirm the tracking file agrees with what is actually in the repo.

Run:

```bash
python check.py
```

This reads `docs/phase-state.json` and prints, per phase: its recorded status, and a best-effort check for whether that phase's expected deliverables exist anywhere in the repo. A `MISMATCH` line means the state file claims more progress than the repo shows — treat this as a signal to investigate before trusting the state file, not something to silently overwrite.

This check is a heuristic (a small hardcoded map of expected directory/file name fragments per phase), not a substitute for actually reading the relevant code when a phase is claimed complete. Use it to decide where to look next, not as the final verification.

## Copilot invocation and scope

Read this skill from `.github/skills/phase-status/SKILL.md` even if a same-named
skill is discovered elsewhere. Resolve the base directory from this SKILL.md's
absolute location. Run the adjacent script with its absolute quoted path, or
change directory to that base first; repository-relative examples assume the
repository root. Python scripts resolve the repo from `__file__`; the Bash script
uses `BASH_SOURCE[0]`. There are no injected skill-directory variables.
Use Python 3.11+ (`python` on Windows, `python3` on Unix if needed).
No blanket shell pre-approval is granted. Respect the current task's write scope.
