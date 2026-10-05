"""Provider-neutral contract (NFR-AI-004) and Anthropic request rules (ADR-0016).

The contract suite runs against every adapter. The OpenAI adapter is a named Phase 3 follow-up
(plan P-3); it must be added to ADAPTER_FACTORIES then and pass the same tests. No network."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.llm.anthropic_adapter import (
    FORBIDDEN_SAMPLING_PARAMS,
    AnthropicAdapter,
    build_chat_kwargs,
    build_provider,
)
from app.integrations.llm.base import (
    LLMConfigurationError,
    LLMError,
    LLMRequest,
    LLMResponse,
    LLMUnavailableError,
)

REQUEST = LLMRequest(
    system="sys",
    user="usr",
    json_schema={"type": "object", "properties": {"topics": {"type": "array"}}},
    model="claude-opus-5-5",
    effort="medium",
    max_output_tokens=2000,
)


class FakeChat:
    def __init__(self, message=None, error: Exception | None = None) -> None:
        self.message = message
        self.error = error
        self.calls: list[list[tuple[str, str]]] = []

    def invoke(self, messages):
        self.calls.append(messages)
        if self.error:
            raise self.error
        return self.message


def message(content="{}", stop="end_turn", usage=(11, 22)):
    return SimpleNamespace(
        content=content,
        response_metadata={"stop_reason": stop},
        usage_metadata={"input_tokens": usage[0], "output_tokens": usage[1]},
    )


def anthropic_with(chat: FakeChat) -> AnthropicAdapter:
    return AnthropicAdapter(chat_factory=lambda request: chat)


ADAPTER_FACTORIES = {"anthropic": anthropic_with}


@pytest.fixture(params=sorted(ADAPTER_FACTORIES))
def make_adapter(request):
    return ADAPTER_FACTORIES[request.param]


# ----------------------------------------------------------- shared contract


def test_contract_returns_text_stop_reason_and_usage(make_adapter):
    adapter = make_adapter(FakeChat(message('{"topics": []}')))
    response = adapter.generate_structured(REQUEST)
    assert isinstance(response, LLMResponse)
    assert response.text == '{"topics": []}'
    assert response.stop_reason == "end_turn"
    assert (response.input_tokens, response.output_tokens) == (11, 22)
    assert response.refused is False
    assert adapter.name


def test_contract_refusal_maps_to_refused(make_adapter):
    response = make_adapter(FakeChat(message("", stop="refusal"))).generate_structured(REQUEST)
    assert response.refused is True


def test_contract_outage_maps_to_unavailable(make_adapter):
    class APIConnectionError(Exception):
        pass

    with pytest.raises(LLMUnavailableError):
        make_adapter(FakeChat(error=APIConnectionError("boom"))).generate_structured(REQUEST)


def test_contract_other_failures_are_llm_errors_not_unavailable(make_adapter):
    with pytest.raises(LLMError) as exc:
        make_adapter(FakeChat(error=ValueError("bad"))).generate_structured(REQUEST)
    assert not isinstance(exc.value, LLMUnavailableError)


def test_contract_http_status_503_and_529_are_unavailable(make_adapter):
    for status in (503, 529, 429):
        err = Exception("x")
        err.status_code = status  # type: ignore[attr-defined]
        with pytest.raises(LLMUnavailableError):
            make_adapter(FakeChat(error=err)).generate_structured(REQUEST)


def test_contract_missing_metadata_defaults_safely(make_adapter):
    bare = SimpleNamespace(content="{}", response_metadata=None, usage_metadata=None)
    response = make_adapter(FakeChat(bare)).generate_structured(REQUEST)
    assert response.stop_reason is None and response.input_tokens == 0 and response.output_tokens == 0


def test_contract_text_blocks_are_joined(make_adapter):
    blocks = [
        {"type": "thinking", "thinking": "..."},
        {"type": "text", "text": '{"a":'},
        {"type": "text", "text": "1}"},
    ]
    response = make_adapter(FakeChat(message(blocks))).generate_structured(REQUEST)
    assert response.text == '{"a":1}'


def test_contract_sends_system_and_user_messages(make_adapter):
    chat = FakeChat(message())
    make_adapter(chat).generate_structured(REQUEST)
    assert chat.calls[0] == [("system", "sys"), ("human", "usr")]


# ------------------------------------------------------- Anthropic specifics


def test_anthropic_request_has_no_temperature_top_p_top_k_or_forced_tool_choice():
    kwargs = build_chat_kwargs(REQUEST, api_key="k", timeout=30.0)
    flat = repr(kwargs)
    for name in (*FORBIDDEN_SAMPLING_PARAMS, "tool_choice"):
        assert name not in kwargs and name not in kwargs["model_kwargs"]
        assert f"'{name}'" not in flat
    assert "tools" not in kwargs and "tools" not in kwargs["model_kwargs"]


def test_effort_set_explicitly():
    kwargs = build_chat_kwargs(REQUEST, api_key=None, timeout=None)
    assert kwargs["model_kwargs"]["output_config"]["effort"] == "medium"
    assert kwargs["model_kwargs"]["output_config"]["format"]["schema"] == REQUEST.json_schema
    assert kwargs["model"] == "claude-opus-5-5" and kwargs["max_tokens"] == 2000
    assert "api_key" not in kwargs and "timeout" not in kwargs


def test_missing_api_key_is_a_configuration_error(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "anthropic_api_key", "")
    with pytest.raises(LLMConfigurationError):
        AnthropicAdapter().generate_structured(REQUEST)


def test_provider_selection_by_configuration():
    assert isinstance(build_provider("anthropic"), AnthropicAdapter)
    with pytest.raises(LLMConfigurationError):
        build_provider("OPENAI")  # adapter arrives in Phase 3 (plan P-3)
