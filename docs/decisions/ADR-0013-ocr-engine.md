# ADR-0013: OCR engine for scanned PDF pages

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Phase 2 (IngestionService); Phase 8 indirectly (Tutor citations depend on OCR text quality)
- **SRS refs:** FR-CON-002; Section 17 "OCR" and "Supported educational content" rows; Section 33 IngestionService; Section 37 "OCR/empty extraction"; AC-004; Section 45 ("should not be expanded with unnecessary infrastructure"); Section 46 OCR risk row

## Context
FR-CON-002 and Section 17 require the ingestion pipeline to detect PDF pages
with no usable text and run OCR on them. If OCR fails, the error must name the
asset and page, and no empty chunks may be created. Scanned material arrives
only as PDF, because direct image uploads are rejected. Section 33 makes OCR
part of the deterministic IngestionService, which must be a reproducible
pipeline. The fixed stack (Section 5.1) does not name an OCR engine.

The SRS leaves two questions open: which engine to use, and how a PDF page is
turned into an image before OCR. The rasteriser is covered by ADR-0014.

## Options

### A. Tesseract 5 through `pytesseract` (recommended)
- The Tesseract binary and the `eng` language data are installed with
  `apt-get` in the backend/celery Docker image. `pytesseract` is a thin
  Python wrapper around that binary.
- **Pros:** Mature and widely used for printed English text. It runs on CPU
  with no ML framework. With a pinned binary, language data, and config
  (`--oem`, `--psm`, DPI), the same image gives the same output, which
  supports the reproducibility rule in Section 33. It returns per-word
  confidence, which can drive the "OCR produced no usable text" failure.
- **Cons:** Handwriting and complex layouts (tables, multi-column) give
  weaker results. It needs a system package in the Dockerfile, not just a pip
  dependency.

### B. OCRmyPDF (wraps Tesseract)
- Adds a text layer to the whole PDF, after which normal text extraction
  runs.
- **Pros:** Good deskew and cleanup, and a single pipeline step.
- **Cons:** It works on whole documents, which makes it harder to OCR only
  the pages without text and to report failures per page (Section 37). It
  also pulls in Ghostscript, qpdf, and more system packages. The OCR engine
  underneath is still Tesseract.

### C. Deep-learning OCR (EasyOCR / PaddleOCR)
- **Pros:** Usually better on photographed pages, unusual fonts, and
  handwriting.
- **Cons:** PaddleOCR adds the PaddlePaddle framework, which is outside the
  fixed stack. EasyOCR adds PyTorch, although ADR-0015 already brings in
  PyTorch for embeddings. Both are much heavier on CPU, slower on a
  demonstration host (ASM-004), and harder to keep bit-reproducible across
  hardware.

## Recommendation
**Option A: Tesseract 5 through `pytesseract`, English (`eng`) only, OCR on
each page.**

Why:
1. It is the smallest addition that meets the SRS. Section 45 asks for no
   unnecessary infrastructure, and Tesseract adds one system package and a
   small Python wrapper.
2. Running OCR page by page fits the SRS directly. "Detect pages without
   usable text" and "identify the affected asset/page" both work at page
   level, and Option B would hide that.
3. With pinned versions and config, the output is reproducible, as Section
   33 requires for a deterministic service.

## Consequences if accepted
- The backend and celery Docker images install `tesseract-ocr` and
  `tesseract-ocr-eng` at pinned versions. The Tesseract version and config
  are written into each OCR stage record, so results can be traced.
- `pytesseract` is added to `backend/pyproject.toml` as an approved
  supporting library, in the same way ADR-0010 approved others.
- **Open for the Phase 2 plan (not decided here):** the "no usable text"
  rule (for example, minimum extracted characters per page) and the
  confidence below which a page is marked OCR-failed. These are
  configuration values, set in the plan.
- Languages other than English, and handwriting, are out of scope until a
  new ADR adds them.
