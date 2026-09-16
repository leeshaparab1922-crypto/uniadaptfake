#!/usr/bin/env python
"""
Reads docs/phase-state.json and cross-checks it against what actually exists
in the repo, so "what phase are we on" never depends on trusting the state
file blindly. Uses only the Python standard library (no jq/pip dependency,
since jq is not guaranteed to be installed on this machine).

Usage: python check.py
"""
import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
STATE_FILE = os.path.join(REPO_ROOT, "docs", "phase-state.json")

# Minimal, hardcoded map of a few structural deliverables expected to exist
# once a given phase is genuinely implemented. Kept intentionally small and
# conservative: false negatives (saying "not found" when it exists under an
# unanticipated path) are safer than false positives here, since the whole
# point is to avoid the agents trusting phase-state.json blindly. Extend this
# map as real phases are implemented and their actual file layout is known.
PHASE_DELIVERABLE_HINTS = {
    1: ["backend", "alembic", "migrations"],
    2: ["ingestion", "curriculum"],
    3: ["question_bank", "assessment"],
    4: ["coverage", "diagnostic"],
    5: ["grading"],
    6: ["learner_model", "mastery"],
    7: ["planner", "study_plan"],
    8: ["tutor", "practice", "quiz"],
    9: ["recommendation", "intervention", "report"],
}


# Directories that hold this workflow's own process/infrastructure files
# (agent definitions, skills, plan/report templates, phase-tracking data) —
# never application code. Excluded so e.g. phase-planner-implementer.md
# (contains "planner") or verification-report-template.md (contains
# "report") don't get mistaken for a phase's actual deliverables.
EXCLUDED_TOP_LEVEL = {".git", "node_modules", ".venv", "__pycache__", ".claude", ".github", ".agents", "SRS_Doc", "docs"}
EXCLUDED_DOCS_SUBDIRS = {"templates", "phases"}


def find_hint_anywhere(hint: str) -> bool:
    """Case-insensitive search for a directory/file name fragment anywhere in
    the repo's application code, skipping this workflow's own process files
    (.claude/, docs/templates/, docs/phases/, docs/phase-state.json) so the
    check reflects real implementation, not the planning scaffolding."""
    hint_lower = hint.lower()
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        rel = os.path.relpath(dirpath, REPO_ROOT)
        top = rel.split(os.sep)[0] if rel != "." else ""
        if top in EXCLUDED_TOP_LEVEL:
            dirnames[:] = []
            continue
        if rel.startswith("docs" + os.sep):
            parts = rel.split(os.sep)
            if len(parts) >= 2 and parts[1] in EXCLUDED_DOCS_SUBDIRS:
                dirnames[:] = []
                continue
        if rel == "docs" and "phase-state.json" in filenames:
            filenames = [f for f in filenames if f != "phase-state.json"]
        for name in dirnames + filenames:
            if hint_lower in name.lower():
                return True
    return False


def main() -> int:
    if not os.path.isfile(STATE_FILE):
        print(f"ERROR: {STATE_FILE} not found.", file=sys.stderr)
        return 1

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    print(f"current_phase: {state.get('current_phase')}  "
          f"phase_name: {state.get('phase_name')}  "
          f"status: {state.get('status')}\n")

    print(f"{'Phase':<6}{'Name':<45}{'Status':<14}{'Deliverables found?':<20}")
    for phase in state.get("phases", []):
        n = phase["phase"]
        hints = PHASE_DELIVERABLE_HINTS.get(n, [])
        found_any = any(find_hint_anywhere(h) for h in hints) if hints else False
        claimed_done = phase["status"] in ("implemented", "verified", "shipped")
        mismatch = ""
        if claimed_done and not found_any:
            mismatch = "  <-- MISMATCH: state file claims progress but no deliverables found in repo"
        elif not claimed_done and found_any:
            mismatch = "  <-- NOTE: deliverables found but state file says not yet done"
        print(f"{n:<6}{phase['name']:<45}{phase['status']:<14}{str(found_any):<20}{mismatch}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
