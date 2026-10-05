# ADR-0014: Document parsers for PDF, PPTX, DOCX, and TXT

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Phase 2 (upload validation, IngestionService); Phase 8 (Tutor citation locators)
- **SRS refs:** FR-CON-001, FR-CON-002, FR-CON-003; Section 17 ("Supported educational content", "Validation", "Cleaning", "Metadata"); NFR-SEC-009; Section 45

## Context
Section 17 accepts four upload formats: PDF, PPTX, DOCX, and UTF-8 TXT, each
up to 25 MB. Legacy DOC/PPT files and direct image uploads are rejected.
FR-CON-003 requires every chunk to keep its source location: a page, slide,
or section. The parser also does the "basic file readability" check in
Section 17 and NFR-SEC-009. The fixed stack does not name any parser. This
ADR chooses one per format. The PDF choice also decides how pages are turned
into images for OCR (ADR-0013).

## Options

### PDF
| Option | Licence | Notes |
|---|---|---|
| **A. `pdfplumber` (pdfminer.six) + `pypdfium2` for rendering pages** (recommended) | MIT / Apache-2.0 or BSD-3 | Extracts text per page with character positions, which helps detect repeated headers and footers during cleaning. Recent `pdfplumber` releases already use `pypdfium2` to render page images, so the OCR rasteriser comes with it. Slower than PyMuPDF, which is acceptable for batch Celery jobs. |
| B. PyMuPDF (`fitz`) | **AGPL-3.0** or commercial | The fastest option, with good text extraction and rendering. Its AGPL licence would apply to the whole backend if it were ever distributed or offered as a network service. That is a licensing decision for a human, not an agent. |
| C. `pypdf` | BSD-3 | Pure Python with no native dependencies. Its text extraction on complex layouts is weaker, and it cannot render pages, so OCR would need a second library. |

### PPTX
| Option | Notes |
|---|---|
| **A. `python-pptx`** (recommended, MIT) | Reads text frames, tables, and speaker notes for each slide. The slide number is the natural locator. |
| B. LibreOffice headless → PDF → PDF parser | Gives a single code path, but adds a very large system dependency and loses slide-level structure. |
| C. `unstructured` | A broad partitioning toolkit with a large dependency tree that overlaps the other choices here. |

### DOCX
| Option | Notes |
|---|---|
| **A. `python-docx`** (recommended, MIT) | Reads paragraphs, heading styles, and tables. DOCX has no fixed pages, so the locator is a section path (nearest heading chain) plus the paragraph index. |
| B. `docx2python` | Similar coverage with fewer users. No advantage here. |
| C. `mammoth` (DOCX → HTML) | Built for converting to HTML. Heading structure would have to be parsed back out of the HTML. |

### TXT
| Option | Notes |
|---|---|
| **A. Python standard library, strict `utf-8` decode** (recommended) | The SRS requires UTF-8 TXT. A decode error rejects the upload with a clear message. The locator is a line range. |
| B. Charset auto-detection (`charset-normalizer`) | Would quietly accept non-UTF-8 files, which the SRS does not allow. |

## Recommendation
- **PDF:** `pdfplumber` for text, with its `pypdfium2` dependency used to
  render pages at a fixed DPI for Tesseract.
- **PPTX:** `python-pptx`. Locator `slide:<n>`. Speaker notes are extracted
  and marked as notes, as an open question for the plan (see below).
- **DOCX:** `python-docx`. Locator `section:<heading path>#p<index>`.
- **TXT:** standard library, strict UTF-8. Locator `lines:<start>-<end>`.

Why:
1. **Licensing.** All recommended libraries use permissive licences. PyMuPDF
   is technically strong, but its AGPL licence needs a human decision, so it
   is not chosen by default.
2. **Locators.** Each recommended library exposes the unit FR-CON-003 needs:
   page, slide, or section.
3. **Fewest dependencies.** The PDF choice covers both text extraction and
   OCR page images, and none of the recommended options adds a system
   package beyond Tesseract (ADR-0013).

## Consequences if accepted
- `pdfplumber`, `pypdfium2`, `python-pptx`, and `python-docx` become
  approved supporting libraries.
- Any document a parser cannot open counts as "unreadable" under Section 17
  and NFR-SEC-009, and fails before it is queued for ingestion.
- **Open for the Phase 2 plan:** whether PPTX speaker notes are ingested;
  how images embedded in PPTX/DOCX are handled (OCR is required only for
  scanned PDFs, so the default is to skip them); and how a known Unit
  boundary is detected inside a multi-Unit file so chunks do not cross it
  (FR-CON-002).
