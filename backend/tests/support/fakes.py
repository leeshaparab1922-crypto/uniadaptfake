"""Deterministic fakes for the ingestion ports.

`FakeObjectStore` exists ONLY so `IngestionService` orchestration can be unit
tested through the `ObjectStore` Protocol. Any test asserting key layout,
write-once behaviour, privacy, scoped credentials, or "bytes are in MinIO"
uses the real compose MinIO service (marker `minio`).
"""

from __future__ import annotations

import hashlib
import math
import re
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import BinaryIO

from app.services.ingestion.chunking import Chunk
from app.services.ingestion.ports import ObjectAlreadyExistsError, OcrResult
from app.services.ingestion_service import IngestionContext


class FakeTokenizer:
    """Whitespace tokens with character offsets; deterministic and dependency-free."""

    def __init__(self, num_special_tokens: int = 0) -> None:
        self.num_special_tokens = num_special_tokens

    def offsets(self, text: str) -> list[tuple[int, int]]:
        return [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]


class FakeEmbedder:
    """Hash-derived unit vectors (dimension 1024 by default)."""

    def __init__(
        self, dimension: int = 1024, *, wrong_dimension: int | None = None, fail_on_call: int | None = None
    ):
        self.dimension = dimension
        self._wrong = wrong_dimension
        self._fail_on_call = fail_on_call
        self.calls = 0
        self.embedded_texts: list[str] = []

    @staticmethod
    def vector_for(text: str, dimension: int = 1024) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < dimension:
            digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
            values.extend((b - 127.5) / 127.5 for b in digest)
            counter += 1
        values = values[:dimension]
        norm = math.sqrt(sum(v * v for v in values))
        return [v / norm for v in values]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        if self._fail_on_call is not None and self.calls == self._fail_on_call:
            raise RuntimeError("simulated embedding failure")
        self.embedded_texts.extend(texts)
        dim = self._wrong or self.dimension
        return [self.vector_for(t, dim) for t in texts]


class FakeOcr:
    """Scripted OCR: `results` is a callable (png_bytes -> OcrResult) or a list consumed in order."""

    def __init__(
        self,
        results: Callable[[bytes], OcrResult] | list[OcrResult] | None = None,
        blank: Callable[[bytes], bool] | None = None,
    ):
        self._results = results
        self._blank = blank or (lambda png: False)
        self.calls = 0

    def ocr_png(self, png_bytes: bytes) -> OcrResult:
        self.calls += 1
        if callable(self._results):
            return self._results(png_bytes)
        if isinstance(self._results, list):
            return self._results.pop(0)
        return OcrResult("", 0.0, "fake-tesseract 5.0", "fake")

    def is_blank(self, png_bytes: bytes, ink_ratio_threshold: float) -> bool:
        return self._blank(png_bytes)


class FakeObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_calls = 0

    def put_if_absent(self, key: str, data: BinaryIO, size: int, content_type: str) -> None:
        if key in self.objects:
            raise ObjectAlreadyExistsError(key)
        self.put_calls += 1
        self.objects[key] = data.read()

    def download_to(self, key: str, dest_path: str) -> None:
        with open(dest_path, "wb") as fh:
            fh.write(self.objects[key])

    def exists(self, key: str) -> bool:
        return key in self.objects


class RecordingQueue:
    def __init__(self, *, fail: bool = False) -> None:
        self.enqueued: list[str] = []
        self._fail = fail

    def enqueue(self, content_version_id: str) -> None:
        if self._fail:
            raise ConnectionError("broker down")
        self.enqueued.append(content_version_id)


@dataclass
class InMemoryRepo:
    """Dict-backed `IngestionRepository` for pure orchestration tests."""

    stage_runs: list[dict] = field(default_factory=list)
    chunks: list[dict] = field(default_factory=list)
    status: str = "PENDING"
    failed_stage: str | None = None
    failure_message: str | None = None
    embedding_config_id: str | None = None
    attempts: int = 0

    def begin_attempt(self, version_id: str) -> int:
        self.attempts += 1
        self.status = "RUNNING"
        return self.attempts

    def stage_succeeded_before(self, version_id: str, stage: str) -> bool:
        return any(r["stage"] == stage and r["status"] == "SUCCEEDED" for r in self.stage_runs)

    def record_stage(
        self, version_id, stage, attempt, status, started_at: datetime, finished_at, detail, error
    ):
        for r in self.stage_runs:
            if r["stage"] == stage and r["attempt"] == attempt:
                r.update(status=status, finished_at=finished_at, detail=detail, error=error)
                return
        self.stage_runs.append(
            dict(
                stage=stage,
                attempt=attempt,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                detail=detail,
                error=error,
            )
        )

    def chunk_count(self, version_id: str) -> int:
        return len(self.chunks)

    def delete_chunks(self, version_id: str) -> None:
        self.chunks.clear()

    def insert_chunks(self, ctx: IngestionContext, chunks: Sequence[Chunk]) -> None:
        for i, c in enumerate(chunks):
            self.chunks.append(dict(id=f"c{i}", index=i, chunk=c, embedding=None))

    def chunks_missing_embeddings(self, version_id: str, limit: int) -> list[tuple[str, str]]:
        return [(c["id"], c["chunk"].text) for c in self.chunks if c["embedding"] is None][:limit]

    def set_embeddings(self, version_id: str, embeddings: dict[str, list[float]]) -> None:
        for c in self.chunks:
            if c["id"] in embeddings:
                c["embedding"] = embeddings[c["id"]]

    def count_missing_embeddings(self, version_id: str) -> int:
        return sum(1 for c in self.chunks if c["embedding"] is None)

    def finalize_success(self, version_id: str, embedding_config_id: str) -> None:
        self.status = "SUCCEEDED"
        self.embedding_config_id = embedding_config_id

    def finalize_failure(self, version_id: str, stage: str, message: str) -> None:
        self.status, self.failed_stage, self.failure_message = "FAILED", stage, message

    def stages(self, attempt: int | None = None) -> list[tuple[str, str]]:
        return [
            (r["stage"], r["status"]) for r in self.stage_runs if attempt is None or r["attempt"] == attempt
        ]


def put_file(store: FakeObjectStore, key: str, data: bytes) -> str:
    store.objects[key] = data
    return hashlib.sha256(data).hexdigest()


def copy_to(path_from: str, path_to: str) -> None:  # pragma: no cover - tiny helper
    shutil.copyfile(path_from, path_to)
