"""FR-CON-002 / AC-004: <=800 tokens, exactly 120 overlap, no Unit crossing, final shorter chunk,
page association retained, deterministic."""

from __future__ import annotations

import pytest

from app.services.ingestion.chunking import chunk_blocks
from app.services.ingestion.unit_boundaries import Block
from tests.support.fakes import FakeTokenizer

TOK = FakeTokenizer()


def words(prefix: str, n: int) -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def block(text, unit=1, locator="page:1", page=1):
    return Block(text, locator, page, unit)


def count(c) -> int:
    return len(c.text.split())


def test_chunks_never_exceed_800_tokens():
    chunks = chunk_blocks([block(words("w", 5000))], TOK)
    assert chunks and all(c.token_count <= 800 and count(c) <= 800 for c in chunks)


def test_exactly_800_tokens_is_a_single_chunk():
    chunks = chunk_blocks([block(words("w", 800))], TOK)
    assert len(chunks) == 1 and chunks[0].token_count == 800


def test_801_tokens_makes_two_chunks_with_120_overlap():
    chunks = chunk_blocks([block(words("w", 801))], TOK)
    assert len(chunks) == 2
    assert chunks[1].text.split()[:120] == chunks[0].text.split()[-120:]


def test_overlap_is_exactly_120_tokens():
    chunks = chunk_blocks([block(words("w", 3000))], TOK)
    for a, b in zip(chunks, chunks[1:], strict=False):
        a_tokens, b_tokens = a.text.split(), b.text.split()
        assert a_tokens[-120:] == b_tokens[:120]


def test_final_short_chunk_allowed():
    chunks = chunk_blocks([block(words("w", 900))], TOK)
    assert chunks[-1].token_count < 800
    assert chunks[-1].text.split()[-1] == "w899"


def test_all_tokens_covered_in_order_without_gaps():
    chunks = chunk_blocks([block(words("w", 2500))], TOK)
    seen = []
    for i, c in enumerate(chunks):
        toks = c.text.split()
        seen.extend(toks if i == 0 else toks[120:])
    assert seen == words("w", 2500).split()


def test_never_crosses_unit_boundary():
    blocks = [block(words("a", 500), unit=1), block(words("b", 500), unit=2)]
    chunks = chunk_blocks(blocks, TOK)
    assert [c.unit_no for c in chunks] == [1, 2]
    assert not any("a499" in c.text and "b0" in c.text for c in chunks)


def test_no_overlap_carried_across_a_unit_boundary():
    chunks = chunk_blocks([block(words("a", 900), unit=1), block(words("b", 900), unit=2)], TOK)
    unit2 = [c for c in chunks if c.unit_no == 2]
    assert unit2[0].text.split()[0] == "b0"


def test_unresolved_unit_blocks_stay_separate_from_numbered_units():
    chunks = chunk_blocks([block("pre amble", unit=None), block("real body", unit=1)], TOK)
    assert [c.unit_no for c in chunks] == [None, 1]


def test_page_association_retained():
    blocks = [
        block(words("a", 300), locator="page:3", page=3),
        block(words("b", 300), locator="page:4", page=4),
    ]
    chunks = chunk_blocks(blocks, TOK)
    assert len(chunks) == 1
    assert chunks[0].locator == "page:3-4" and chunks[0].page_no == 3 and chunks[0].locator_type == "PAGE"


def test_chunk_starting_on_later_page_carries_that_pages_locator():
    blocks = [
        block(words("a", 800), locator="page:1", page=1),
        block(words("b", 800), locator="page:2", page=2),
    ]
    chunks = chunk_blocks(blocks, TOK)
    assert chunks[0].locator.startswith("page:1")
    assert chunks[-1].locator.endswith("2") and chunks[-1].page_no in (1, 2)


def test_section_and_lines_locators_pass_through():
    c = chunk_blocks([Block("hello world", "section:Unit 1#p1", None, 1)], TOK)[0]
    assert (c.locator, c.locator_type, c.page_no) == ("section:Unit 1#p1", "SECTION", None)
    c = chunk_blocks([Block("hello world", "lines:3-4", None, 1)], TOK)[0]
    assert c.locator_type == "LINES"


def test_special_tokens_count_toward_the_800_limit():
    tok = FakeTokenizer(num_special_tokens=2)
    chunks = chunk_blocks([block(words("w", 3000))], tok)
    assert all(c.token_count <= 800 for c in chunks)
    assert max(len(c.text.split()) for c in chunks) == 798


def test_empty_blocks_give_no_chunks():
    assert chunk_blocks([], TOK) == []
    assert chunk_blocks([block("   ")], TOK) == []


def test_chunking_is_deterministic():
    blocks = [block(words("w", 2000))]
    assert chunk_blocks(blocks, TOK) == chunk_blocks(blocks, TOK)


def test_invalid_window_or_overlap_rejected():
    with pytest.raises(ValueError):
        chunk_blocks([block("a b c")], TOK, max_tokens=100, overlap=100)
    with pytest.raises(ValueError):
        chunk_blocks([block("a b c")], TOK, max_tokens=100, overlap=-1)


def test_text_is_sliced_from_the_source_not_reconstructed():
    text = "alpha,  beta\nGamma"  # punctuation and spacing preserved
    assert chunk_blocks([block(text)], TOK)[0].text == text
