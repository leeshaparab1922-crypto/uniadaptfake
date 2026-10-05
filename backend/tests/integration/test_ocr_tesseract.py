"""Real Tesseract binary (ADR-0013). Marker: tesseract (runs inside the backend Docker/CI image)."""

from __future__ import annotations

import pytest

from app.integrations.ocr import TesseractOcrEngine
from app.services.ingestion.parsers.base import parse_document
from tests.support import docs

pytestmark = pytest.mark.tesseract


def _render(tmp_path, pages):
    path = tmp_path / "scan.pdf"
    path.write_bytes(docs.make_scanned_pdf(pages))
    doc = parse_document(str(path), "pdf", min_page_chars=25, render_dpi=300, include_pptx_notes=True)
    return doc


def test_scanned_pdf_ocr_text_extracted(tmp_path):
    doc = _render(tmp_path, ["Unit 1 Introduction\nArrays and linked lists"])
    result = TesseractOcrEngine().ocr_png(doc.render_png(1))
    doc.close()
    assert "Unit" in result.text and "Arrays" in result.text
    assert result.mean_confidence >= 60 and result.engine_version.startswith("5")
    assert "--oem 1 --psm 3" in result.config


def test_ocr_output_deterministic_across_runs(tmp_path):
    doc = _render(tmp_path, ["Binary search trees\nTraversal orders"])
    png = doc.render_png(1)
    doc.close()
    engine = TesseractOcrEngine()
    assert engine.ocr_png(png) == engine.ocr_png(png)


def test_blank_page_detected_and_text_page_is_not(tmp_path):
    doc = _render(tmp_path, [None, "Some visible text on this page"])
    engine = TesseractOcrEngine()
    assert engine.is_blank(doc.render_png(1), 0.001) is True
    assert engine.is_blank(doc.render_png(2), 0.001) is False
    doc.close()
