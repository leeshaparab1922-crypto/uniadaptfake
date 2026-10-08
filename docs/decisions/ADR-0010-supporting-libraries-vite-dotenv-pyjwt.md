# ADR-0010: Allow Vite, python-dotenv, and PyJWT as supporting libraries

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 scaffolding; every later phase (build tooling, config, auth)
- **SRS refs:** Section 5.1 fixed stack; Section 45 ("should not be expanded with unnecessary infrastructure")

## Context
The fixed stack names React 18, JWT, and Docker, but not the frontend build
tool, the library that loads `.env` files, or the JWT library. Each of these
supports a technology already in the stack and replaces none of them.

## Decision
- **Vite** is the frontend build and dev-server tool for React 18 + TypeScript.
- **python-dotenv** loads `.env` in local development only. In Docker and
  production, settings come from real environment variables.
- **PyJWT** is the JWT library (not `python-jose`, which is less actively
  maintained).

## Consequences
- Later phases use these three and do not introduce alternatives (for example
  webpack, CRA, or python-jose) without a new, human-approved ADR.
- This ADR does not open the door to other additions. Any further library or
  infrastructure still needs its own human decision.
