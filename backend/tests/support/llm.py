"""Fake LLM provider and fixture helpers for Curriculum Agent tests. No network, no API key."""

from __future__ import annotations

import json
from pathlib import Path

from app.integrations.llm.base import LLMRequest, LLMResponse

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "curriculum"


def fixture_text(name: str) -> str:
    return (FIXTURES / f"{name}.json").read_text(encoding="utf-8")


def fixture_json(name: str) -> dict:
    return json.loads(fixture_text(name))


class FakeLLMProvider:
    """Replays scripted responses. Items: str (model text), LLMResponse, or an Exception to raise."""

    name = "FAKE"

    def __init__(self, *responses: str | LLMResponse | Exception) -> None:
        self._responses = list(responses)
        self.requests: list[LLMRequest] = []

    def generate_structured(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("FakeLLMProvider has no more scripted responses")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, str):
            return LLMResponse(text=item, stop_reason="end_turn", input_tokens=100, output_tokens=200)
        return item
