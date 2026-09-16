---
name: verify-live
description: "Verify UniAdapt AI's implemented/verified/shipped phases against the SRS, the actual repo code, and the running site via Playwright/chromium-cli. Use when asked to verify a phase end-to-end, audit progress against the SRS, or check the live site matches what phase-state.json claims."
---

# Verify Live

Two-part verification for UniAdapt AI phases already marked `implemented`,
`verified`, or `shipped` in `docs/phase-state.json`:

1. **Static trace** — does the SRS's FR-*/BUS-*/AC-* set for that phase actually
   show up in the repo's code, and does the phase's own plan.md /
   verification-report.md exist and say PASS?
2. **Live-site check** — start the real app and drive it with `chromium-cli`
   to confirm the claimed features actually work, not just that files exist.

Run the static trace first (Part 1). Only move to Part 2 once there is an
actual app to start — `backend/`, `frontend/`, and a `docker-compose.yml` (or
equivalent) must exist, which they won't until Phase 1 is implemented.

## Part 1 — Static trace (run this first, always)

```bash
python .github/skills/verify-live/scripts/audit_phases.py
```

No argument audits every phase currently claimed `implemented`/`verifying`/
`verified`/`blocked`/`shipped`. Pass a phase number to force-audit one phase
regardless of its recorded status:

```bash
python .github/skills/verify-live/scripts/audit_phases.py 1
```

For each phase in scope, it prints:
- Whether `plan.md` and `verification-report.md` exist, and the report's
  recorded verdict (`PASS`/`BLOCKED`).
- Every FR-*/BUS-*/AC-* ID the SRS's Section 43 row assigns to that phase
  (ranges like `FR-AUTH-001..004` are expanded to individual IDs), and
  whether that exact ID string appears anywhere in application code
  (`.claude/`, `.agents/`, `docs/`, `SRS_Doc/` are excluded as scaffolding,
  not application code).

Exit code is `1` if any gap is found (missing report PASS verdict, or a
requirement ID with zero references anywhere in code), `0` otherwise.

**A `MISSING` requirement ID is a prompt to go read that area of the code
yourself, not proof the feature is unbuilt** — code doesn't have to cite
`FR-AUTH-001` in a comment to implement it. Treat the script's output as a
worklist for a human/agent code read, not a final verdict. Cross-reference
against the phase's own `plan.md` file list to see what was actually supposed
to change.

## Part 2 — Live-site verification (only once an app exists to run)

This part has **not been run against a real instance in this repo** — no
phase has been implemented yet, so there is no `backend/`, `frontend/`, or
compose file to start. The steps below are written from Section 5's fixed
stack (FastAPI + React 18, `docker compose` per the SRS's implementation
baseline) and from this repo's own `CLAUDE.md`/`AGENTS.md` conventions, but
they are unverified until the first phase ships. Update this section with the
actual working commands the first time you run it for real, and remove this
paragraph once verified.

### Start the app

```bash
docker compose up -d --build
timeout 60 bash -c 'until curl -sf http://localhost:8000/health >/dev/null; do sleep 2; done'   # backend
timeout 60 bash -c 'until curl -sf http://localhost:5173 >/dev/null; do sleep 2; done'           # frontend (Vite default port — confirm against actual repo config)
```

Adjust host/ports to whatever the phase's `docker-compose.yml` and
`plan.md` actually specify — the above are placeholders from common
FastAPI/Vite defaults, not confirmed values from this repo.

### Drive it

For each requirement ID the static trace (Part 1) confirmed is in scope for
the phase under test, translate its AC-* Given/When/Then scenario (look it
up with `bash .github/skills/srs-lookup/lookup.sh <AC-ID>`) into a `chromium-cli`
script. Example shape, using Phase 1's FR-AUTH-001 (login) as a template —
**not yet run against a real instance**:

```bash
chromium-cli --session verify <<'EOF'
nav http://localhost:5173/login
wait-for text=Sign in
fill input[name="email"] admin@example.edu
fill input[name="password"] correct-horse-battery-staple
click button:has-text("Sign in")
wait-for text=Dashboard
screenshot
console --errors
EOF
```

Screenshots land in `chromium_cli/sessions/verify/screenshots/`
(latest symlinked as `screenshot.png`). Confirm these paths against the installed
browser tool. Use its `help` command; do not assume a Claude-specific browser
skill is installed in Copilot.

Repeat one representative flow per FR-* in the phase's scope — the goal is
one real interaction per requirement that proves the claimed behavior,
not exhaustive UI coverage. For requirements that are API-only (no UI, e.g.
most of Phase 1's admin/CSV-import FRs per its own Expected-Demo bar), drive
them with `curl` against the API instead of `chromium-cli`:

```bash
curl -sf -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.edu","password":"correct-horse-battery-staple"}' | python -m json.tool
```

### Stop cleanly

```bash
docker compose down
```

## Gotchas

- **Static trace has no notion of "correct," only "present."** A requirement
  ID grep-matching in a comment or a stale/dead code path still counts as
  `OK`. Read the actual matched line, don't just trust the marker.
- **The live-site section above is unverified against this repo** — no phase
  has shipped an app yet. Treat every command in Part 2 as a draft to correct
  against the real `docker-compose.yml`/`plan.md` the first time you run it,
  not as confirmed fact.

## Copilot invocation and scope

Read this skill from `.github/skills/verify-live/SKILL.md` even if a same-named
skill is discovered elsewhere. Resolve the base directory from this SKILL.md's
absolute location. Run the adjacent script with its absolute quoted path, or
change directory to that base first; repository-relative examples assume the
repository root. Python scripts resolve the repo from `__file__`; the Bash script
uses `BASH_SOURCE[0]`. There are no injected skill-directory variables.
Use Python 3.11+ (`python` on Windows, `python3` on Unix if needed).
No blanket shell pre-approval is granted. Respect the current task's write scope.

Adapter clarification: the static script reads the requirement ranges from phase
state; it does not independently derive BUS/AC coverage from SRS tables. You must
perform the fresh SRS/plan comparison above yourself. A missing plan is reported;
a missing PASS contributes exit 1 specifically for verified/shipped phases.
All `.github/`, `.claude/`, `.agents/`, and `docs/` files are excluded from code
trace evidence. Live commands remain drafts, not validated application tests.
Use Git Bash for the Bash examples on Windows; choose available Playwright or
chromium-cli tooling without assuming a Claude plugin is installed. Exercise both
positive and negative AC scenarios and record evidence for both.
