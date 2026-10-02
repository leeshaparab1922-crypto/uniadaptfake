# UniAdapt AI - Local Development Setup

Full requirements live in `SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md`.
Phase workflow docs: `.claude/README.md`.

## Prerequisites

- **Backend: Python 3.11 or 3.12 only** (`requires-python = ">=3.11,<3.13"`).
  Newer interpreters (e.g. 3.14) are not supported. Use Docker, or create a
  3.11/3.12 virtualenv:
  ```bash
  cd backend
  py -3.12 -m venv .venv          # Windows; or: python3.11 -m venv .venv
  .venv/Scripts/activate           # Linux/macOS: source .venv/bin/activate
  pip install -e ".[dev]"
  ```
- **Frontend:** Node.js with npm (`cd frontend && npm install`).
- PostgreSQL 15 (pgvector) and Redis, most easily via `docker compose up postgres redis`.

## Environment file

Copy `.env.example` to `.env` (never commit `.env`).

**Local HTTP development:** the auth cookies are `Secure` by default
(`COOKIE_SECURE=true`), which browsers will not send over plain
`http://localhost`, so login appears to succeed but the session is lost. For
local HTTP dev only, set this in your local `.env`:

```
COOKIE_SECURE=false
```

Leave it `true` for any deployed/HTTPS environment.

## Database, seed data and running

```bash
cd backend
alembic upgrade head
python -m scripts.seed_demo_data      # idempotent; safe to re-run
uvicorn app.main:app --reload         # http://localhost:8000

cd ../frontend
npm run dev                           # http://localhost:5173
```

### Demo logins (all use the password `ChangeMe123!`)

| Role    | Email                      |
|---------|----------------------------|
| Admin   | `admin.demo@example.com`   |
| Teacher | `teacher.demo@example.com` |
| Student | `student.demo@example.com` |

These use `example.com` because the API validates emails with Pydantic's
`EmailStr`, which rejects special-use domains such as `.test`.
If you seeded a database before this change, the old `*@uniadapt.test`
accounts remain in it and cannot log in; they can be ignored or deleted.

## Tests and checks

```bash
cd backend && python -m pytest                       # uses in-memory SQLite
cd frontend && npx tsc -b && npm run lint && npm test
```
