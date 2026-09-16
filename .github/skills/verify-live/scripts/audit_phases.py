#!/usr/bin/env python
"""
Cross-checks every phase docs/phase-state.json claims is implemented/verified/
shipped against:
  1. The SRS's own FR-*/BUS-*/AC-* IDs for that phase (via Section 43 + 12/11/40).
  2. Actual repo code — does anything reference those requirement IDs, and do
     the phase's own plan.md / verification-report.md exist and say PASS?

This is a static check only. It does not start the app or touch the network.
Pair it with the "Run (agent path)" section of SKILL.md for the live-site
Playwright pass once a phase actually has a running app to point at.

Usage: python audit_phases.py [phase_number]
  No argument: audits every phase whose status is implemented/verified/shipped.
  A phase number: audits just that phase regardless of its recorded status.
"""
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
STATE_FILE = os.path.join(REPO_ROOT, "docs", "phase-state.json")
SRS_FILE = os.path.join(
    REPO_ROOT, "SRS_Doc",
    "UniAdapt_AI_Business_and_Software_Requirements_Specification.md",
)
LOOKUP_SCRIPT = os.path.join(REPO_ROOT, ".github", "skills", "srs-lookup", "lookup.sh")

CLAIMED_DONE_STATUSES = {"implemented", "verifying", "verified", "blocked", "shipped"}

EXCLUDED_TOP_LEVEL = {".git", "node_modules", ".venv", "__pycache__", ".agents", ".claude", ".github", "docs", "SRS_Doc"}
EXCLUDED_DOCS_SUBDIRS = {"templates"}
# Root-level status files restate requirement-ID ranges (e.g. "FR-AUTH-001..004")
# in their auto-generated phase table — that's a reference to the range, not
# evidence the requirement is implemented in code. Exclude by exact filename.
EXCLUDED_ROOT_FILES = {"AGENTS.md", "CLAUDE.md"}


def expand_id_range(spec: str):
    """'FR-AUTH-001..004' -> ['FR-AUTH-001', ..., 'FR-AUTH-004']. A bare ID
    passes through unchanged."""
    m = re.match(r"^([A-Z]+-[A-Z]+)-(\d+)\.\.(\d+)$", spec)
    if not m:
        return [spec]
    prefix, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
    width = len(m.group(2))
    return [f"{prefix}-{str(n).zfill(width)}" for n in range(lo, hi + 1)]


def load_state():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def grep_repo_for_id(req_id: str) -> list:
    """Returns list of 'path:line' for every occurrence of req_id in
    application code (never in .claude/.agents/docs/SRS_Doc scaffolding)."""
    hits = []
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
        for name in filenames:
            if name.endswith((".pyc", ".png", ".jpg", ".jpeg", ".pdf", ".lock")):
                continue
            if rel == "." and name in EXCLUDED_ROOT_FILES:
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if req_id in line:
                            hits.append(f"{os.path.relpath(path, REPO_ROOT)}:{i}")
            except (OSError, UnicodeDecodeError):
                continue
    return hits


def check_plan_and_report(phase: dict) -> dict:
    result = {"plan_exists": False, "report_exists": False, "report_verdict": None}
    plan_path = phase.get("plan_path")
    if plan_path and os.path.isfile(os.path.join(REPO_ROOT, plan_path)):
        result["plan_exists"] = True
    report_path = phase.get("verification_report_path")
    if report_path:
        full = os.path.join(REPO_ROOT, report_path)
        if os.path.isfile(full):
            result["report_exists"] = True
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            m = re.search(r"\b(PASS|BLOCKED)\b", text)
            if m:
                result["report_verdict"] = m.group(1)
    return result


def main() -> int:
    if not os.path.isfile(STATE_FILE):
        print(f"ERROR: {STATE_FILE} not found.", file=sys.stderr)
        return 1
    if not os.path.isfile(SRS_FILE):
        print(f"ERROR: SRS file not found at {SRS_FILE}.", file=sys.stderr)
        return 1

    state = load_state()
    only_phase = int(sys.argv[1]) if len(sys.argv) > 1 else None

    phases = state.get("phases", [])
    if only_phase is not None:
        phases = [p for p in phases if p["phase"] == only_phase]
        if not phases:
            print(f"ERROR: no phase {only_phase} in {STATE_FILE}.", file=sys.stderr)
            return 1
    else:
        phases = [p for p in phases if p["status"] in CLAIMED_DONE_STATUSES]

    if not phases:
        print("No phase is currently claimed implemented/verified/shipped. Nothing to audit.")
        return 0

    overall_gap_found = False

    for phase in phases:
        n = phase["phase"]
        name = phase["name"]
        status = phase["status"]
        print(f"\n{'=' * 70}")
        print(f"Phase {n} - {name}  (recorded status: {status})")
        print("=" * 70)

        ids = []
        for spec in phase.get("srs_requirements", []):
            ids.extend(expand_id_range(spec))

        pr = check_plan_and_report(phase)
        print(f"  plan.md exists:                {pr['plan_exists']}")
        print(f"  verification-report.md exists: {pr['report_exists']}"
              + (f"  (verdict: {pr['report_verdict']})" if pr["report_verdict"] else ""))
        if status in ("verified", "shipped") and pr["report_verdict"] != "PASS":
            print("  !! MISMATCH: state file says phase is verified/shipped but its own "
                  "verification-report.md does not record a PASS verdict.")
            overall_gap_found = True

        print(f"\n  Requirement IDs in scope ({len(ids)}): {', '.join(ids)}")
        print("\n  Per-requirement code trace:")
        missing = []
        for req_id in ids:
            hits = grep_repo_for_id(req_id)
            marker = "OK" if hits else "MISSING"
            if not hits:
                missing.append(req_id)
            print(f"    [{marker:7}] {req_id}" + (f"  ({len(hits)} reference(s), e.g. {hits[0]})" if hits else ""))

        if missing:
            print(f"\n  !! {len(missing)} requirement ID(s) have NO reference anywhere in "
                  f"application code: {', '.join(missing)}")
            print("     This does not necessarily mean the feature is unbuilt - code may not "
                  "cite requirement IDs directly. Treat this as 'needs a human/agent read', "
                  "not a hard failure. Cross-check against the phase's own plan.md file list.")
            overall_gap_found = True

    print(f"\n{'=' * 70}")
    if overall_gap_found:
        print("RESULT: gaps found above. Do not trust phase-state.json's status for these "
              "phases without reading the flagged areas directly.")
    else:
        print("RESULT: no gaps found by static trace. This does NOT confirm the feature "
              "actually works - run the live-site Playwright pass (see SKILL.md) once the "
              "app is running.")
    print("=" * 70)

    return 1 if overall_gap_found else 0


if __name__ == "__main__":
    raise SystemExit(main())
