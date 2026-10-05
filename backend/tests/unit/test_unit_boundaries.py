"""Plan P-6: Teacher-selected Unit, deterministic heading detection, unresolved pre-heading text."""

from __future__ import annotations

import pytest

from app.services.ingestion.parsers.base import Segment
from app.services.ingestion.unit_boundaries import UnitRef, assign_units, heading_number, roman_to_int

UNITS = [UnitRef(1, "Basics"), UnitRef(2, "Trees"), UnitRef(3, "Graphs")]


@pytest.mark.parametrize(
    "line,n",
    [
        ("Unit 2", 2),
        ("UNIT-3: Graphs", 3),
        ("Module IV", 4),
        ("unit ii", 2),
        ("Unit 1 - Intro", 1),
        ("Unit.2 X", 2),
        ("Module 3 Graph Algorithms (8 hrs)", 3),
        ("Unit 4 (8 hours)", 4),
        ("Unit 2: trees", 2),
    ],
)
def test_heading_forms_recognised(line, n):
    assert heading_number(line) == n


@pytest.mark.parametrize(
    "line",
    [
        "This unit is hard",
        "Units of measure",
        "Community",
        "u" * 200,
        "Module",
        # Finding m2: a wrapped sentence that starts with "Unit N" is prose, not a heading.
        "Unit 2 covers the remaining topics",
        "Unit 3 and 4 are optional",
        "Unit.2 x",
    ],
)
def test_non_headings_ignored(line):
    assert heading_number(line) is None


def test_roman_numerals():
    assert [roman_to_int(x) for x in ("i", "iv", "ix", "xiv", "q")] == [1, 4, 9, 14, None]


def test_fixed_unit_applies_to_every_segment():
    segs = [Segment("a", "page:1", 1), Segment("Unit 2 heading", "page:2", 2)]
    blocks, report = assign_units(segs, units=UNITS, fixed_unit_no=3)
    assert [b.unit_no for b in blocks] == [3, 3] and report.headings_matched == 0


def test_headings_switch_unit_and_text_before_first_heading_is_unresolved():
    segs = [Segment("Course preamble\nUnit 1: Basics\nlists\nUnit 2: Trees\nbst", "page:1", 1)]
    blocks, report = assign_units(segs, units=UNITS)
    assert [(b.unit_no, b.text) for b in blocks] == [
        (None, "Course preamble"),
        (1, "Unit 1: Basics\nlists"),
        (2, "Unit 2: Trees\nbst"),
    ]
    assert report.headings_matched == 2 and report.unresolved_blocks == 1


def test_unit_carries_across_segments_until_next_heading():
    segs = [
        Segment("Unit 1\nintro", "page:1", 1),
        Segment("more intro", "page:2", 2),
        Segment("Unit 3\ngraphs", "page:3", 3),
    ]
    blocks, _ = assign_units(segs, units=UNITS)
    assert [b.unit_no for b in blocks] == [1, 1, 3]


def test_heading_number_beyond_subject_units_is_ignored_not_guessed():
    segs = [Segment("Unit 1\nx\nUnit 9\ny", "page:1", 1)]
    blocks, report = assign_units(segs, units=UNITS)
    assert [b.unit_no for b in blocks] == [1] and report.ignored_headings == 1


def test_heading_maps_to_nth_unit_by_order_index_not_by_value():
    units = [UnitRef(10, "A"), UnitRef(20, "B")]
    blocks, _ = assign_units([Segment("Unit 2\nbody", "page:1", 1)], units=units)
    assert blocks[0].unit_no == 20


def test_no_headings_and_no_fixed_unit_leaves_everything_unresolved():
    blocks, report = assign_units([Segment("plain text", "lines:1-1")], units=UNITS)
    assert [b.unit_no for b in blocks] == [None] and report.headings_matched == 0


def test_blank_segments_produce_no_blocks():
    blocks, _ = assign_units([Segment("  ", "page:1", 1)], units=UNITS, fixed_unit_no=1)
    assert blocks == []


def test_wrapped_sentence_does_not_switch_the_unit():
    text = "Unit 1: Basics\nlists and\nUnit 2 covers trees next term\nmore lists"
    segs = [Segment(text, "page:1", 1)]
    blocks, report = assign_units(segs, units=UNITS)
    assert [b.unit_no for b in blocks] == [1] and report.headings_matched == 1
