# ADR-0001: JWT carried in an httpOnly cookie with CSRF protection

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 (auth), every later phase that adds UI or API routes
- **SRS refs:** NFR-SEC-004, FR-AUTH-001..004. The frontend rules deferred this choice to Phase 1.

## Context
The SRS fixes JWT (4-hour expiry, no refresh tokens, `token_version`
revocation) but not where the browser keeps it. localStorage is readable by any
script, so a single XSS bug would leak the session.

## Decision
- The backend sets the JWT in a cookie with `HttpOnly`, `Secure` (disabled only
  for local HTTP development via config), `SameSite=Strict`, `Path=/`, and
  `Max-Age` of 4 hours.
- CSRF uses the double-submit pattern: the backend issues a non-httpOnly
  `csrf_token` cookie, the frontend echoes it in an `X-CSRF-Token` header on
  every state-changing request (POST/PUT/PATCH/DELETE), and the backend rejects
  mismatches with `403`.
- The frontend never reads, stores, or logs the JWT. The API client sends
  cookies (`credentials: "include"` / `withCredentials: true`).
- Logout clears the cookie **and** increments `token_version` (NFR-SEC-004).
- CORS allows only the configured frontend origin, with credentials.

## Consequences
- The frontend has no token-handling logic to get wrong.
- Every new mutating route in later phases must pass the CSRF check.
  Verification treats a missing check as blocking.
- Migration path: switching to `Authorization: Bearer` later changes only the
  transport layer (one backend dependency plus the API client), not the JWT.
