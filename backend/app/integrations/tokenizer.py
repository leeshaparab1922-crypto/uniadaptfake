"""bge-m3 tokenizer (ADR-0015): loaded from the *same pinned revision* as the
embedding model so "800 embedding-model tokens" is exactly what the model sees."""

from __future__ import annotations

from app.core.config import settings


class BgeM3Tokenizer:
    def __init__(self, *, model_id: str | None = None, revision: str | None = None) -> None:
        from transformers import AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(
            model_id or settings.embedding_model_id,
            revision=revision or settings.embedding_model_revision,
            use_fast=True,
            cache_dir=settings.hf_home,
        )
        self._tok.model_max_length = 10**9  # chunking, not the tokenizer, enforces the 800 limit
        self.num_special_tokens = self._tok.num_special_tokens_to_add(pair=False)

    def offsets(self, text: str) -> list[tuple[int, int]]:
        enc = self._tok(text, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
        return [(int(s), int(e)) for s, e in enc["offset_mapping"]]
