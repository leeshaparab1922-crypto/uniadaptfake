# ADR-0012: Password reset is issued by an Admin only (no self-service)

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 (auth); any later account-recovery work
- **SRS refs:** FR-AUTH-004 (Pre/Trigger: Admin creates or selects the account and generates the token; out-of-band URL delivery by Admin), NFR-SEC-015/016

## Decision
- Only an Admin can issue a password-reset token
  (`POST /admin/accounts/{id}/password-resets`). There is no public "forgot
  password" endpoint.
- The Admin delivers the single-use, expiring reset URL out of band.
- Consuming a reset token is public but rate limited (ADR-0006), returns
  messages that don't reveal whether an account exists, and increments
  `token_version` (NFR-SEC-004).

## Consequences
- No email or SMS infrastructure is needed, consistent with the fixed stack.
- Adding self-service reset later requires a new ADR and an SRS basis.
