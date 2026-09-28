"""Domain-level exceptions raised by the service layer.

Services stay framework-agnostic (no `fastapi.HTTPException` inside
`app/services/**`, per `.claude/rules/backend.md`'s route/service
separation). `app/main.py` maps each of these to an HTTP status code via a
single set of exception handlers, so error responses are consistent and
never leak internals (NFR-SEC-011).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all service-layer errors."""


class ValidationError(DomainError):
    """Input failed a business validation rule. Maps to 400."""


class AuthenticationError(DomainError):
    """Login/token failure. Message must be generic (NFR-SEC-016) - never
    reveal which specific check failed. Maps to 401."""


class ForbiddenError(DomainError):
    """Caller is authenticated but not authorized for this action. Maps to 403."""


class NotFoundError(DomainError):
    """Referenced entity does not exist. Maps to 404."""


class ConflictError(DomainError):
    """Action conflicts with current state (e.g. capacity, duplicate). Maps to 409."""


class RateLimitedError(DomainError):
    """Caller exceeded a configured rate limit (NFR-SEC-016). Maps to 429."""
