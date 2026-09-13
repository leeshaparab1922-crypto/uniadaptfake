# Phase <N> — <Phase Name> — Verification Report

## Phase

- Phase number: <N>
- Phase name: <name>
- Plan reference: docs/phases/phase-<N>-<kebab-name>/plan.md

## Requirement-by-Requirement Verification

| ID | Expected (from SRS) | Found in implementation | Pass/Fail | Notes |
|---|---|---|---|---|

Include both positive and negative AC-* scenarios explicitly. Any BUS-* rule violation is a blocking failure, never a style note. For phases touching Sections 23/24/25, include a line-by-line diff of the implemented formula against the SRS text.

## Regression Test Results

- Full existing test suite run: pass/fail summary.
- Confirmation that previously "shipped" phases still work as before.
- Confirmation that this phase's declared dependencies (Section 43) are genuinely integrated, not just present.

## Code Reviewer Findings

(Delegated to `agent-skills:code-reviewer` — five axes: correctness, readability, architecture, security, performance. Embed or link its findings here.)

## Overall Verdict

**PASS** (ready to ship) or **BLOCKED** (list blocking issues below).

## Blocking Issues

(Only if BLOCKED — itemized list, each traceable to a requirement ID above.)

## Shipment Record

(Filled in only after Step 7 — shipping — runs, and only after a fresh human go-ahead.)

- Branch:
- Commit(s):
- PR URL:
- Shipped at:
