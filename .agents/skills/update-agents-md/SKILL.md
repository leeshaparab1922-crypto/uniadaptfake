---
name: update-agents-md
description: >-
  Regenerate the project-root AGENTS.md's phase-status section from docs/phase-state.json,
  keeping it current with real implementation progress. Run after a phase is implemented
  so anyone opening the repo sees up-to-date status without reading docs/phase-state.json directly.
---

# Update AGENTS.md

Regenerates the auto-generated phase-status block in the repo-root `AGENTS.md`
from `docs/phase-state.json`. Run this after any change to `phase-state.json` —
in normal workflow use, that means `phase-planner-implementer` calls this at
the end of its implement step, right after marking a phase `"implemented"`.

Run:

```bash
python .agents/skills/update-agents-md/scripts/generate.py
```

Behavior:
- If `AGENTS.md` doesn't exist yet, creates it with a short static project
  overview plus the generated status table.
- If `AGENTS.md` exists and contains the
  `<!-- BEGIN AUTO-GENERATED PHASE STATUS -->` /
  `<!-- END AUTO-GENERATED PHASE STATUS -->` marker pair, replaces only the
  content between those markers — everything else in the file is preserved untouched.
- If the markers are missing, appends the generated section at the end rather than guessing
  where to inject it — it never overwrites or discards existing hand-written content.
