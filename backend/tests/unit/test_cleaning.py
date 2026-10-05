"""SRS Section 17 'Cleaning': header/footer removal, noise, boundaries kept, meaning untouched."""

from __future__ import annotations

from dataclasses import replace

from app.services.ingestion import cleaning
from app.services.ingestion.parsers.base import Segment


def _pages(
    n,
    header="UniAdapt Institute - Data Structures",
    footer_fmt="Page {i} of {n}",
    body_fmt="Body text of page {i} is unique.",
):
    return [
        Segment(f"{header}\n{body_fmt.format(i=i)}\n{footer_fmt.format(i=i, n=n)}", f"page:{i}", page_no=i)
        for i in range(1, n + 1)
    ]


def test_repeated_header_footer_removed_page_boundaries_kept():
    cleaned = cleaning.clean_segments(_pages(5))
    assert [s.locator for s in cleaned] == [f"page:{i}" for i in range(1, 6)]
    for i, seg in enumerate(cleaned, start=1):
        assert seg.text == f"Body text of page {i} is unique."


def test_page_numbers_with_different_digits_match_as_same_footer():
    cleaned = cleaning.clean_segments(_pages(4, header="Dept of CSE"))
    assert all("Page" not in s.text for s in cleaned)


def test_non_repeating_edge_lines_are_kept():
    segs = [Segment(f"Unique title {i}\nbody {i}", f"page:{i}", page_no=i) for i in range(1, 5)]
    assert [s.text for s in cleaning.clean_segments(segs)] == [s.text for s in segs]


def test_fewer_than_three_pages_never_stripped():
    segs = _pages(2)
    assert [s.text for s in cleaning.clean_segments(segs)] == [s.text for s in segs]


def test_repeated_unit_heading_is_not_treated_as_header():
    segs = [Segment(f"Unit 1 Basics\nbody {i}", f"page:{i}", page_no=i) for i in range(1, 5)]
    assert all(s.text.startswith("Unit 1 Basics") for s in cleaning.clean_segments(segs))


def test_noise_control_characters_and_space_runs_normalised():
    seg = Segment("a\x00b​  c\t\td e\r\n\r\n\r\n\r\nf", "lines:1-2")
    assert cleaning.clean_segments([seg])[0].text == "ab c d e\n\nf"


def test_academic_text_is_not_rewritten():
    text = "Time complexity: O(n log n); x-\nray test 3.14159 != 3.14"
    out = cleaning.normalize_text(text)
    assert "O(n log n)" in out and "3.14159" in out and "x-\nray" in out


def test_emptied_segments_dropped_but_ocr_pending_pages_kept():
    segs = [Segment("   ", "page:1", page_no=1), Segment("", "page:2", page_no=2, needs_ocr=True)]
    out = cleaning.clean_segments(segs)
    assert [s.locator for s in out] == ["page:2"]


def test_notes_segments_not_subject_to_header_removal():
    segs = [Segment("Footer\nnote body", f"slide:{i}#notes", page_no=i) for i in range(1, 5)]
    assert all("Footer" in s.text for s in cleaning.clean_segments(segs))


def test_cleaning_is_deterministic():
    segs = _pages(6)
    assert cleaning.clean_segments(segs) == cleaning.clean_segments([replace(s) for s in segs])
