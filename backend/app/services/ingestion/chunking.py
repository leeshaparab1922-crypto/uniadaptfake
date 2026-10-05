"""Deterministic chunking (FR-CON-002, SRS Section 17, ADR-0015).

Rules, implemented exactly:
- a chunk holds at most 800 embedding-model tokens *including* the tokenizer's
  special tokens (so what the model sees never exceeds 800);
- consecutive chunks overlap by exactly 120 tokens;
- a chunk never crosses a Unit boundary (each Unit group is chunked on its own,
  so no overlap is carried across units);
- a final shorter chunk is allowed;
- every chunk keeps the locator/page of the source it starts in.

Tokens are counted with the embedding model's own tokenizer through the
`Tokenizer` port (same pinned revision as the model).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby

from app.services.ingestion import locators
from app.services.ingestion.ports import Tokenizer
from app.services.ingestion.unit_boundaries import Block

BLOCK_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class Chunk:
    text: str
    unit_no: int | None
    locator: str
    locator_type: str
    page_no: int | None
    token_count: int  # content tokens + special tokens


def _chunk_group(blocks: list[Block], tokenizer: Tokenizer, max_tokens: int, overlap: int) -> list[Chunk]:
    window = max_tokens - tokenizer.num_special_tokens
    if window <= overlap or overlap < 0:
        raise ValueError("Chunk window must be larger than the (non-negative) overlap.")

    spans: list[tuple[int, int, Block]] = []
    parts: list[str] = []
    cursor = 0
    for block in blocks:
        start = cursor
        parts.append(block.text)
        cursor += len(block.text)
        spans.append((start, cursor, block))
        parts.append(BLOCK_SEPARATOR)
        cursor += len(BLOCK_SEPARATOR)
    text = "".join(parts).rstrip("\n")

    offsets = tokenizer.offsets(text)
    n = len(offsets)
    chunks: list[Chunk] = []
    start = 0
    while n > 0:
        end = min(start + window, n)
        char_start, char_end = offsets[start][0], offsets[end - 1][1]
        piece = text[char_start:char_end].strip()
        if piece:
            touched = [b for (s, e, b) in spans if s < char_end and e > char_start]
            first, last = (touched[0], touched[-1]) if touched else (blocks[0], blocks[-1])
            locator = locators.merge(first.locator, last.locator)
            chunks.append(
                Chunk(
                    text=piece,
                    unit_no=blocks[0].unit_no,
                    locator=locator,
                    locator_type=locators.locator_type(locator),
                    page_no=first.page_no,
                    token_count=(end - start) + tokenizer.num_special_tokens,
                )
            )
        if end >= n:
            break
        start = end - overlap
    return chunks


def chunk_blocks(
    blocks: list[Block], tokenizer: Tokenizer, *, max_tokens: int = 800, overlap: int = 120
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for _, group in groupby(blocks, key=lambda b: b.unit_no):
        chunks.extend(_chunk_group(list(group), tokenizer, max_tokens, overlap))
    return chunks
