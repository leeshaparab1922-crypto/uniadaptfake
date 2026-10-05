"""Local CPU embedding with BAAI/bge-m3 at a pinned revision (ADR-0015).

Dense output only, `normalize_embeddings=True` (cosine similarity), no
`trust_remote_code`. Weights are cached under `HF_HOME` (a Docker volume), and
course content never leaves the deployment."""

from __future__ import annotations

from collections.abc import Sequence

from app.core.config import settings
from app.models.embedding_config import EMBEDDING_DIMENSION


class BgeM3Embedder:
    dimension = EMBEDDING_DIMENSION

    def __init__(self, *, model_id: str | None = None, revision: str | None = None) -> None:
        self._model_id = model_id or settings.embedding_model_id
        self._revision = revision or settings.embedding_model_revision
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self._model_id,
                revision=self._revision,
                device="cpu",
                trust_remote_code=False,
                cache_folder=settings.hf_home,
            )
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(
            list(texts),
            batch_size=settings.embedding_batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [[float(x) for x in row] for row in vectors]
