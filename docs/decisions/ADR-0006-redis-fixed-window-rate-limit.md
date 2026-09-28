# ADR-0006: Redis fixed-window rate limiting with limits in configuration

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 (login, invitation acceptance, password reset), Phase 8 (Tutor), any later abuse-sensitive endpoint
- **SRS refs:** NFR-SEC-016

## Decision
- Algorithm: a fixed-window counter in Redis (`INCR` on a key, plus `EXPIRE` for
  the window), with one key per (endpoint, account) and one per
  (endpoint, client IP).
- All limits and window lengths are environment settings documented in
  `.env.example`, not hard-coded, because NFR-SEC-016 requires them to be
  configurable.
- One shared helper (for example `app/core/rate_limit.py`) is used by every
  rate-limited endpoint. No per-endpoint copies.
- Throttled and failed attempts return the same generic message, so responses
  never reveal whether an account exists.

## Consequences
- The simplest mechanism to read and debug, and Redis is already in the fixed stack.
- Known trade-off: requests can burst at window boundaries. That is acceptable
  here. A later ADR can switch the helper to a sliding window without changing
  its callers.
