"""Ingestion-specific failures. These are permanent (non-retryable) unless
stated: the Teacher must replace/clean the source file."""

from __future__ import annotations

from app.core.errors import ValidationError

EMPTY_EXTRACTION_MESSAGE = (
    "Text could not be extracted from this content. Upload a clearer file or enter a reference."
)


class UnreadableDocumentError(ValidationError):
    """The file cannot be opened/parsed (SRS Section 17 'basic file readability')."""


class IngestionFailure(Exception):
    """A pipeline stage failed in a way that retrying will not fix."""

    def __init__(self, stage: str, message: str, detail: dict | None = None) -> None:
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.detail = detail or {}


class IngestionSkip(Exception):
    """This delivery must not run the pipeline at all; the version is left as it is."""


class IngestionInProgress(IngestionSkip):
    """Another worker is already running this version and is still active (finding m1).
    The duplicate delivery does nothing."""


class IngestionNotNeeded(IngestionSkip):
    """The version already SUCCEEDED or is no longer DRAFT (finding N2): a delayed duplicate
    delivery must not set it back to RUNNING."""


class TransientIngestionError(Exception):
    """Infrastructure hiccup (object store, model load, ...): safe to retry/resume."""
