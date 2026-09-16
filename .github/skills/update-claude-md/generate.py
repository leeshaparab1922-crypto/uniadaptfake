#!/usr/bin/env python
"""
Regenerates the project-root CLAUDE.md from docs/phase-state.json plus a
short, hand-maintained project overview block. This script only touches the
auto-generated section of CLAUDE.md (between the BEGIN/END markers below) —
anything a human writes outside those markers is preserved verbatim.

Usage: python generate.py

Uses only the Python standard library (no jq/pip dependency).
"""
import datetime
import json
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
STATE_FILE = os.path.join(REPO_ROOT, "docs", "phase-state.json")
CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")

BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED PHASE STATUS (update-claude-md skill) -->"
END_MARKER = "<!-- END AUTO-GENERATED PHASE STATUS (update-claude-md skill) -->"

STATUS_LABELS = {
    "not_started": "Not started",
    "planned": "Planned (awaiting approval)",
    "plan_approved": "Plan approved (awaiting implementation)",
    "implementing": "Implementing",
    "implemented": "Implemented (awaiting verification)",
    "verifying": "Verifying",
    "verified": "Verified (ready to ship)",
    "blocked": "Blocked",
    "shipped": "Shipped",
}


def build_auto_section(state: dict) -> str:
    lines = [BEGIN_MARKER, ""]
    lines.append(f"_Last regenerated: {datetime.datetime.now().isoformat(timespec='seconds')}_")
    lines.append("")
    lines.append(f"**Current phase:** {state.get('current_phase')} — "
                 f"{state.get('phase_name')} ({STATUS_LABELS.get(state.get('status'), state.get('status'))})")
    lines.append("")
    lines.append("| Phase | Name | Status | SRS Requirements | Dependencies | Plan | Verification | PR |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for phase in state.get("phases", []):
        reqs = ", ".join(phase.get("srs_requirements", [])) or "-"
        deps = ", ".join(phase.get("dependencies", [])) or "None"
        status = STATUS_LABELS.get(phase.get("status"), phase.get("status"))
        plan_link = f"[plan]({phase['plan_path']})" if phase.get("plan_path") else "-"
        report_link = f"[report]({phase['verification_report_path']})" if phase.get("verification_report_path") else "-"
        pr_link = f"[PR]({phase['shipped_pr']})" if phase.get("shipped_pr") else "-"
        lines.append(f"| {phase['phase']} | {phase['name']} | {status} | {reqs} | {deps} | {plan_link} | {report_link} | {pr_link} |")
    lines.append("")
    lines.append("Full workflow details: [`.github/README.md`](.github/README.md). "
                 "Raw tracking data: [`docs/phase-state.json`](docs/phase-state.json). "
                 "Full spec: [`SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md`]"
                 "(SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md).")
    lines.append("")
    lines.append(END_MARKER)
    return "\n".join(lines)


STATIC_HEADER = """# UniAdapt AI

UniAdapt AI is a department-wise adaptive learning platform for one engineering
college, connecting academic structure, approved course content, actual
classroom coverage, diagnostic evidence, and student availability to produce
explainable daily/weekly study plans. Three roles only: Admin, Teacher, Student.

Full requirements: [`SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md`](SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md)
(48 sections — use the `srs-lookup` skill for targeted lookups rather than
reading it end to end).

Implementation proceeds one SRS Section-43 phase at a time via a two-agent
GitHub Copilot workflow (`phase-planner-implementer` plans/implements,
`implementation-verifier-shipper` verifies/reviews/ships), always gated on
explicit human approval between steps. Full workflow docs:
[`.github/README.md`](.github/README.md).

The status table below is auto-generated from `docs/phase-state.json` by the
`update-claude-md` skill, run by `phase-planner-implementer` after it finishes
implementing each phase. Do not hand-edit the block between the markers —
edits there are overwritten on the next regeneration. Anything outside the
markers (including this section) is preserved as-is.
"""


def main() -> int:
    if not os.path.isfile(STATE_FILE):
        print(f"ERROR: {STATE_FILE} not found.")
        return 1

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    auto_section = build_auto_section(state)

    if os.path.isfile(CLAUDE_MD):
        with open(CLAUDE_MD, "r", encoding="utf-8") as f:
            existing = f.read()
        if BEGIN_MARKER in existing and END_MARKER in existing:
            pre = existing.split(BEGIN_MARKER)[0].rstrip("\n")
            post = existing.split(END_MARKER)[1].lstrip("\n")
            new_content = pre + "\n\n" + auto_section + ("\n\n" + post if post else "\n")
        else:
            # Markers missing (e.g. a human rewrote the file) — append the
            # auto section rather than guessing where to inject it, so we
            # never silently discard hand-written content.
            new_content = existing.rstrip("\n") + "\n\n" + auto_section + "\n"
    else:
        new_content = STATIC_HEADER.rstrip("\n") + "\n\n" + auto_section + "\n"

    with open(CLAUDE_MD, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"CLAUDE.md regenerated at {CLAUDE_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
