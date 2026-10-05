"""Dependency-injection ports so IngestionService stays pure and unit-testable
(`.claude/rules/backend.md`): real adapters live in `app.integrations`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import BinaryIO, Protocol


class ObjectAlreadyExistsError(Exception):
    """Write-once violation (ADR-0018): the key already exists."""


class ObjectStore(Protocol):
    def put_if_absent(self, key: str, data: BinaryIO, size: int, content_type: str) -> None: ...

    def download_to(self, key: str, dest_path: str) -> None: ...

    def exists(self, key: str) -> bool: ...


@dataclass(frozen=True)
class OcrResult:
    text: str
    mean_confidence: float
    engine_version: str
    config: str


class OcrEngine(Protocol):
    def ocr_png(self, png_bytes: bytes) -> OcrResult: ...

    def is_blank(self, png_bytes: bytes, ink_ratio_threshold: float) -> bool:
        """True when the rendered page is visually blank (nothing to OCR; plan P-4)."""
        ...


class Tokenizer(Protocol):
    """Embedding-model tokenizer (ADR-0015: same pinned revision as the model)."""

    num_special_tokens: int

    def offsets(self, text: str) -> list[tuple[int, int]]:
        """(start, end) character offsets of each content token, no special tokens."""
        ...


class Embedder(Protocol):
    dimension: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class IngestionQueue(Protocol):
    def enqueue(self, content_version_id: str) -> None: ...
