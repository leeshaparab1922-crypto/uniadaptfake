"""Real BAAI/bge-m3 at the pinned revision (ADR-0015). Marker: hf_model (large download, HF_HOME cache)."""

from __future__ import annotations

import math

import pytest

from app.core.config import settings
from app.integrations.embedding import BgeM3Embedder
from app.integrations.tokenizer import BgeM3Tokenizer
from app.services.ingestion.chunking import chunk_blocks
from app.services.ingestion.unit_boundaries import Block

pytestmark = pytest.mark.hf_model


def test_bge_m3_dim_1024_normalized_and_800_token_chunk_not_truncated():
    tokenizer = BgeM3Tokenizer()
    text = " ".join(f"concept{i} explains data structures" for i in range(1500))
    chunks = chunk_blocks([Block(text, "page:1", 1, 1)], tokenizer, max_tokens=800, overlap=120)
    assert len(chunks) >= 2 and all(c.token_count <= 800 for c in chunks)
    re_encoded = tokenizer._tok(chunks[0].text, add_special_tokens=True)["input_ids"]  # noqa: SLF001
    assert len(re_encoded) <= 800  # what the model sees never exceeds the chunk limit
    vectors = BgeM3Embedder().embed([chunks[0].text, "binary trees"])
    assert all(len(v) == 1024 for v in vectors)
    assert all(abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-3 for v in vectors)


def test_embedding_config_matches_pinned_revision_and_is_recorded():
    assert settings.embedding_model_id == "BAAI/bge-m3"
    assert settings.embedding_model_revision == "5617a9f61b028005a4858fdac845db406aefb181"
    assert BgeM3Tokenizer().num_special_tokens == 2


def test_similar_texts_score_higher_than_unrelated():
    a, b, c = BgeM3Embedder().embed(
        ["binary search tree", "BST data structure", "monsoon rainfall in Kerala"]
    )
    dot = lambda x, y: sum(p * q for p, q in zip(x, y, strict=True))  # noqa: E731
    assert dot(a, b) > dot(a, c)
