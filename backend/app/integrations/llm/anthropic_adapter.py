"""Anthropic adapter through `langchain-anthropic` (ADR-0016).

API behaviours of `claude-opus-5-5` this adapter honours:

* Forced `tool_choice` (`any` / a named tool) is rejected with HTTP 400, so structured output
  uses the native JSON-schema output format. No tool is bound and `tool_choice` is never sent.
* Thinking cannot be disabled, so effort is always set explicitly (it is also stored in
  `ai_provider_configurations` and therefore recorded for every run).
* `temperature`, `top_p` and `top_k` cannot be set and are never sent.
* The `refusal` stop reason is surfaced as `LLMResponse.refused`.

Spike S-1 status: the exact `langchain-anthropic` pass-through for `output_config` could not be
confirmed against the live API on the machine that wrote this adapter (no API key, no network
calls by decision). All request shaping lives in `build_chat_kwargs()` so a one-line change
fixes it if the live smoke test (`-m llm_live`) shows the parameter name differs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.integrations.llm.base import (
    LLMConfigurationError,
    LLMError,
    LLMRequest,
    LLMResponse,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

FORBIDDEN_SAMPLING_PARAMS = ("temperature", "top_p", "top_k")
_UNAVAILABLE_ERROR_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
    "OverloadedError",
    "ServiceUnavailableError",
    "ConnectError",
    "ReadTimeout",
}
_UNAVAILABLE_STATUS = {408, 429, 500, 502, 503, 504, 529}


def build_chat_kwargs(request: LLMRequest, *, api_key: str | None, timeout: float | None) -> dict[str, Any]:
    """Constructor arguments for `ChatAnthropic`. Pure and secret-free apart from `api_key`."""
    kwargs: dict[str, Any] = {
        "model": request.model,
        "max_tokens": request.max_output_tokens,
        "model_kwargs": {
            "output_config": {
                "effort": request.effort,
                "format": {"type": "json_schema", "schema": request.json_schema},
            }
        },
    }
    if timeout is not None:
        kwargs["timeout"] = timeout
    if api_key:
        kwargs["api_key"] = api_key
    return kwargs


def _default_chat_factory(request: LLMRequest) -> Any:
    if not settings.anthropic_api_key:
        raise LLMConfigurationError("ANTHROPIC_API_KEY is not set; curriculum generation is unavailable.")
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:  # pragma: no cover - depends on the deployment image
        raise LLMConfigurationError("langchain-anthropic is not installed.") from exc
    return ChatAnthropic(
        **build_chat_kwargs(
            request,
            api_key=settings.anthropic_api_key,
            timeout=float(settings.llm_request_timeout_seconds),
        )
    )


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


def _is_unavailable(exc: BaseException) -> bool:
    if type(exc).__name__ in _UNAVAILABLE_ERROR_NAMES:
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and status in _UNAVAILABLE_STATUS


class AnthropicAdapter:
    name = "ANTHROPIC"

    def __init__(self, chat_factory: Callable[[LLMRequest], Any] | None = None) -> None:
        self._chat_factory = chat_factory or _default_chat_factory

    def generate_structured(self, request: LLMRequest) -> LLMResponse:
        chat = self._chat_factory(request)
        try:
            message = chat.invoke([("system", request.system), ("human", request.user)])
        except LLMError:
            raise
        except Exception as exc:
            if _is_unavailable(exc):
                logger.warning("Anthropic unavailable: %s", type(exc).__name__)
                raise LLMUnavailableError("The AI provider is unavailable right now.") from exc
            raise LLMError(f"AI provider call failed ({type(exc).__name__}).") from exc
        metadata = getattr(message, "response_metadata", None) or {}
        usage = getattr(message, "usage_metadata", None) or {}
        return LLMResponse(
            text=_text_of(getattr(message, "content", "")),
            stop_reason=metadata.get("stop_reason"),
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
        )


def build_provider(provider_name: str) -> Any:
    """Adapter selected by deployment configuration. OpenAI is a Phase 3 follow-up (plan P-3)."""
    if provider_name.upper() == "ANTHROPIC":
        return AnthropicAdapter()
    raise LLMConfigurationError(
        f"AI provider {provider_name!r} has no adapter yet (OpenAI arrives in Phase 3)."
    )
