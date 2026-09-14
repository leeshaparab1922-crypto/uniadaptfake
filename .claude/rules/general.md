---
description: Project-wide standards for UniAdapt AI — fixed stack, AI/deterministic boundary, testing philosophy, security baseline. Always loaded.
---

# UniAdapt AI — General Rules

These rules are advisory context, not enforcement. Where a rule must hold
unconditionally, it is backed by a hook in `.claude/hooks/*.sh` wired through
`.claude/settings.json` — see `.claude/README.md` for what's actually enforced
versus what's guidance.

## Fixed stack — no substitutions

The implementation baseline (SRS Section 5.1) is fixed:

React 18, TypeScript, Tailwind, Redux Toolkit, React Query, Recharts, FastAPI,
Python 3.11, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 15 with pgvector,
Redis, MinIO, Celery, LangGraph/LangChain, JWT, bcrypt, Docker, Docker Compose.

Do not add a new framework, library, database, queue, or infrastructure
component outside this list without a human decision recorded in an SRS
amendment or ADR. This is SRS Section 45's constraint ("the fixed source
stack... should not be expanded with unnecessary infrastructure"), not a
style preference.

## AI-vs-deterministic boundary

LangGraph/LangChain may coordinate and sequence calls to the five
deterministic services (`IngestionService`, `DiagnosticEngine`, `AutoGrader`,
`LearnerModelService`, `StudyPlannerService`), but must never wrap their
output in further LLM reasoning, and must never let an LLM alter, re-score,
or second-guess their deterministic results. Prompts live in a versioned
registry outside these services' code (NFR-MNT-001). This is the single
highest-risk architectural rule in the SRS (Sections 33/34) — see
`.claude/rules/deterministic-services.md` for the full detail and a
per-change checklist.

## No unnecessary infrastructure

Before proposing any new dependency, service, or infrastructure component,
check it against the fixed stack above. If it's not on the list, it needs a
human decision first, not an in-the-moment addition.

## Testing philosophy

- The five deterministic services need ≥80% automated test coverage
  including boundary and failure cases (NFR-TST-001).
- Every phase ships unit/integration tests, seed/demo data, and documented
  acceptance evidence (NFR-TST-002).
- See `.claude/rules/backend.md` and `.claude/rules/frontend.md` for
  tool-specific detail (pytest vs. Vitest, coverage tooling, etc.).

## Security baseline

SRS Section 36 (NFR-SEC-004..016) governs authentication, secret handling,
uploads, sandboxed code execution, and audit trails — full detail lives in
`.claude/rules/backend.md` since these apply overwhelmingly to backend code.
One rule applies everywhere without exception: no agent ever places a
secret, credential, or `.env` value in source control.
