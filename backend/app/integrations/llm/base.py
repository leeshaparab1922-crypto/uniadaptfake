"""Provider-neutral LLM interface (SRS Section 32, NFR-AI-004, ADR-0016).

Agents depend only on `LLMProvider`; deployment configuration picks the adapter. The Anthropic
adapter exists now; the OpenAI adapter is a named Phase 3 follow-up (plan P-3), validated by
the same contract tests (`tests/unit/test_llm_provider_contract.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception):
    """Base class for provider failures."""


class LLMUnavailableError(LLMError):
    """The provider could not be reached or is overloaded (ASM-004): queue a retry, never a partial draft."""


class LLMConfigurationError(LLMError):
    """Missing key, package, or unsupported configuration. Not retryable."""


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str
    json_schema: dict  # JSON schema of the strict Pydantic output model
    model: str
    effort: str
    max_output_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    text: str  # raw model output (expected to be one JSON document)
    stop_reason: str | None
    input_tokens: int
    output_tokens: int

    @property
    def refused(self) -> bool:
        """ADR-0016: the `refusal` stop reason is a failed run, never an empty graph."""
        return self.stop_reason == "refusal"


class LLMProvider(Protocol):
    name: str

    def generate_structured(self, request: LLMRequest) -> LLMResponse: ...
