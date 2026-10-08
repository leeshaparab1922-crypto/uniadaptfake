# ADR-0009: Enum columns stored as VARCHAR + CHECK, not native Postgres ENUM

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** the Phase 1 migration and every later Alembic migration

## Context
Native Postgres ENUM types are awkward to change. Adding, removing, or renaming a
value needs special `ALTER TYPE` handling in Alembic, and removing one means
rebuilding the type. Later phases will add statuses.

## Decision
- In Python, fixed-choice fields are string `enum.Enum` classes.
- In SQLAlchemy, map them with `Enum(..., native_enum=False,
  create_constraint=True, length=<n>)`. This produces a `VARCHAR` column plus a
  named `CHECK` constraint.
- CHECK constraints are named consistently so Alembic can drop and recreate them
  when the allowed values change.

## Consequences
- Adding a value takes one ordinary migration that drops and recreates the CHECK.
- Database-portable, with the same Python API as native enums.
