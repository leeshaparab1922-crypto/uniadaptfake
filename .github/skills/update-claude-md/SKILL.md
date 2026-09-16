---
name: update-claude-md
description: "Regenerate the project-root CLAUDE.md's phase-status section from docs/phase-state.json, keeping it current with real implementation progress. Run after a phase is implemented so anyone (human or agent) opening the repo sees up-to-date status without reading docs/phase-state.json directly."
---

# Update CLAUDE.md

Regenerates the auto-generated phase-status block in the repo-root `CLAUDE.md`
from `docs/phase-state.json`. Run this after any change to `phase-state.json` —
in normal workflow use, that means `phase-planner-implementer` calls this at
the end of its implement step, right after marking a phase `"implemented"`.

Run:

```bash
python generate.py
```

Behavior:
- If `CLAUDE.md` doesn't exist yet, creates it with a short static project
  overview plus the generated status table.
- If `CLAUDE.md` exists and contains the
  `<!-- BEGIN AUTO-GENERATED PHASE STATUS -->` /
  `<!-- END AUTO-GENERATED PHASE STATUS -->` marker pair, replaces only the
  content between those markers — everything else in the file (hand-written
  notes, conventions, anything a human added) is preserved untouched.
- If the markers are missing (e.g. someone rewrote the file by hand without
  them), appends the generated section at the end rather than guessing where
  to inject it — it never overwrites or discards existing hand-written content.

This script only reads `docs/phase-state.json` — it does not re-derive phase
status from scratch, so it is fast and safe to call often. It does not replace
the `phase-status` skill's repo-vs-state-file mismatch check; run that
separately if you suspect the state file itself may be stale.

## Copilot invocation and scope

Read this skill from `.github/skills/update-claude-md/SKILL.md` even if a same-named
skill is discovered elsewhere. Resolve the base directory from this SKILL.md's
absolute location. Run the adjacent script with its absolute quoted path, or
change directory to that base first; repository-relative examples assume the
repository root. Python scripts resolve the repo from `__file__`; the Bash script
uses `BASH_SOURCE[0]`. There are no injected skill-directory variables.
Use Python 3.11+ (`python` on Windows, `python3` on Unix if needed).
No blanket shell pre-approval is granted. Respect the current task's write scope.

This skill deliberately still updates root `CLAUDE.md`, not `AGENTS.md` or
Copilot instructions. Do not run the generator on the real repository when the
user has prohibited root-file changes (including during this port's validation).
The actual markers include `(update-claude-md skill)` before `-->`.
