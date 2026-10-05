"""FR-CON-003 mandatory locators (ADR-0014)."""

from __future__ import annotations

import pytest

from app.core.errors import ValidationError
from app.services.ingestion import locators


def test_locator_formats():
    assert locators.page(7) == "page:7"
    assert locators.slide(3) == "slide:3" and locators.slide(3, notes=True) == "slide:3#notes"
    assert locators.section(["Unit 2", "Trees"], 14) == "section:Unit 2 > Trees#p14"
    assert locators.section([], 1) == "section:(document)#p1"
    assert locators.lines(40, 95) == "lines:40-95" and locators.lines(9, 3) == "lines:3-9"


@pytest.mark.parametrize("bad", [None, "", "   ", "foo:1", "page:", "7"])
def test_null_empty_or_malformed_locator_rejected(bad):
    with pytest.raises(ValidationError):
        locators.validate(bad)


def test_types_and_page_numbers():
    assert locators.locator_type("page:2") == "PAGE"
    assert locators.locator_type("slide:2#notes") == "SLIDE"
    assert locators.locator_type("section:A#p1") == "SECTION"
    assert locators.locator_type("lines:1-2") == "LINES"
    assert locators.page_no_of("page:5-6") == 5
    assert locators.page_no_of("slide:4") == 4
    assert locators.page_no_of("lines:1-2") is None


def test_merge_ranges():
    assert locators.merge("page:3", "page:3") == "page:3"
    assert locators.merge("page:3", "page:5") == "page:3-5"
    assert locators.merge("lines:1-4", "lines:9-12") == "lines:1-12"
    assert locators.merge("slide:2", "slide:2#notes") == "slide:2"
    assert locators.merge("section:A#p1", "section:A#p9") == "section:A#p1"
