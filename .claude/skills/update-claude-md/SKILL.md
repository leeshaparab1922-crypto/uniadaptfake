---
name: update-claude-md
description: Regenerate the project-root CLAUDE.md's phase-status section from docs/phase-state.json, keeping it current with real implementation progress. Run after a phase is implemented so anyone (human or agent) opening the repo sees up-to-date status without reading docs/phase-state.json directly.
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/generate.py *)
shell: bash
---

# Update CLAUDE.md

Regenerates the auto-generated phase-status block in the repo-root `CLAUDE.md`
from `docs/phase-state.json`. Run this after any change to `phase-state.json` —
in normal workflow use, that means `phase-planner-implementer` calls this at
the end of its implement step, right after marking a phase `"implemented"`.

Run:

```bash
python ${CLAUDE_SKILL_DIR}/generate.py
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
