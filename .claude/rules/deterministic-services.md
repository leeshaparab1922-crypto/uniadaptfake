---
description: The AI-vs-deterministic architectural boundary for UniAdapt AI's five deterministic services — the highest-risk rule in the SRS.
paths:
  - "backend/app/services/**"
  - "SRS_Doc/**"
---

# UniAdapt AI — Deterministic Services Boundary

This file exists because SRS Section 46 explicitly calls for elevated-risk
treatment of the Mastery Score / Engagement Score / Adaptive Study Planner
algorithms and their surrounding boundary. An LLM silently reordering or
influencing a Mastery Score would be a correctness-breaking, hard-to-detect
bug — worth its own narrowly-scoped rules file rather than one paragraph
buried in `backend.md`.

## The hard boundary (SRS Sections 33/34)

The five deterministic services — `IngestionService`, `DiagnosticEngine`,
`AutoGrader`, `LearnerModelService`, `StudyPlannerService` — must be pure,
auditable, and repeatable. LangGraph/LangChain may coordinate batch and
runtime chains around them, but:

- It must never wrap these services in LLM reasoning.
- It must never alter, re-score, or second-guess their results.
- These services must never call an LLM internally.
- Prompts used elsewhere in the system must live in a versioned registry
  outside these services' code (NFR-MNT-001).

Per Section 34's AI-vs-Deterministic Responsibility Matrix: AI may draft,
rank, and narrate; deterministic code owns schema checks, grading
correctness, and all mastery/engagement/planning math; certain actions
additionally require a human (Teacher/Subject Owner) approval gate. Treat
this matrix as the source of truth for which layer owns what.

## Checklist for any change touching these services

Before completing a change under `backend/app/services/**`, confirm:

- [ ] Does this add an LLM call inside a deterministic function? (Not
      allowed — stop and reconsider the design.)
- [ ] Does this change a formula constant or term without updating the
      SRS-cited docstring that documents it?
- [ ] Is there a boundary/failure-case test covering this change (empty
      input, malformed input, out-of-range values, edge-of-range values)?
- [ ] Does the function remain pure and unit-testable without network/DB
      mocking?

## Versioned test fixtures

SRS Section 46's risk mitigation mandates treating Sections 21–25, 28, and
35–36 as versioned test fixtures — any change to the formulas or thresholds
they describe requires boundary tests before phase acceptance, not just a
manual smoke test.
