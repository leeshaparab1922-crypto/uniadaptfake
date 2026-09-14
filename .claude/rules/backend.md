---
description: Backend (FastAPI/Python) coding standards, structure, testing, and security rules for UniAdapt AI.
paths:
  - "backend/**/*.py"
  - "backend/**"
---

# UniAdapt AI — Backend Rules

## Stack pin

FastAPI, Python 3.11, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 15 with
pgvector, Redis, MinIO, Celery, LangGraph/LangChain, JWT, bcrypt. See
`.claude/rules/general.md` for the full fixed-stack rule.

## Project structure (starting convention)

```
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── workers/
│   └── db/
├── tests/
│   ├── unit/
│   └── integration/
└── alembic/
    └── versions/
```

This is a starting convention for Phase 1 to create. If Phase 1's `plan.md`
proposes something different, that's fine as long as it's documented in the
plan — this is not a locked contract.

## Naming conventions

- snake_case for modules, functions, variables.
- PascalCase for Pydantic and SQLAlchemy classes.
- `_service.py` suffix for the five deterministic services.
- `test_*.py` mirroring the source module name.

## Deterministic services rule (NFR-MNT-001, hard)

`IngestionService`, `DiagnosticEngine`, `AutoGrader`, `LearnerModelService`,
`StudyPlannerService` must be:

- Pure functions/classes with no hidden global state.
- Fully unit-testable without network/DB mocking where possible.
- Documented per formula term, with docstrings citing the exact SRS section
  (23/24/25 for Mastery Score / Engagement Score / Adaptive Study Planner).
- Never calling an LLM from inside these services.

See `.claude/rules/deterministic-services.md` for the full boundary rule and
a per-change checklist — it loads automatically when you touch
`backend/app/services/**`.

## API / schema convention (NFR-MNT-002)

- Every endpoint has a Pydantic request/response schema — no raw dicts.
- Rely on FastAPI's generated OpenAPI docs; don't hand-write API docs that
  can drift from the code.
- All DB schema changes go through Alembic migrations only — never hand-edit
  the database or use `Base.metadata.create_all` outside test fixtures.

## Testing (NFR-TST-001 / NFR-TST-002)

- pytest + pytest-cov.
- ≥80% coverage on the five deterministic services, including boundary and
  failure-case tests (empty input, malformed input, out-of-range scores,
  concurrent-write edge cases as applicable).
- Every phase ships seed/demo data and documents acceptance evidence in that
  phase's `verification-report.md`.

## Security rules relevant to code review (SRS Section 36)

- **JWT**: 4-hour expiry, no refresh tokens; use a `token_version`
  column/claim for revocation (cite the exact NFR-SEC ID at implementation
  time).
- **Passwords**: bcrypt only; never log or store plaintext passwords; never
  include password fields in a log statement or exception message.
- **Authorization**: role-scoped queries, not just route guards — every
  Teacher/Student data query must filter by ownership/department at the
  query level, not rely solely on a `requires_role` decorator on the route.
- **Uploads**: 25MB limit plus MIME validation enforced server-side.
- **Sandboxed code execution**: network off, 1 CPU / 256MB memory / 10s
  startup / 5s per test / 30s total / 1MB output caps (NFR-SEC-003/010).
- **No secrets in source control** — config via environment variables or a
  gitignored `.env` file only.
- **TLS required** in production configs.
- **Audit trail required** on approvals, overrides, and grade changes — an
  audit log write is part of "done" for any endpoint performing these
  actions, not an afterthought.

## Lint / format / test tools

- **Ruff** — lint and format (replaces both flake8 and black).
- **mypy** — strict-ish type checking.
- **pytest** (+ pytest-cov) — testing and coverage.

These are not yet configured in the repo (no `pyproject.toml` exists). When
Phase 1 scaffolds `backend/`, it should add:

- `pyproject.toml` with `[tool.ruff]`, `[tool.mypy]`, and
  `[tool.pytest.ini_options]` (coverage target ≥80% on `app/services/`).
- A `backend/Makefile` or `backend/scripts/lint.sh` for a one-shot local
  lint/format/test command.
