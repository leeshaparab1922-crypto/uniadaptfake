# ADR-0019: Allow the minio SDK, pgvector (Python), Pillow, and the minio/mc image as supporting libraries

- **Status:** Accepted
- **Date:** 2026-10-04
- **Affects:** Phase 2 (slice 2A ingestion); every later phase that reads uploaded content or vectors
- **SRS refs:** Section 5.1 fixed stack (PostgreSQL 15 with pgvector, MinIO); Section 17 "Storage"; Section 45; `.claude/rules/general.md` ("No unnecessary infrastructure")

## Context
Slice 2A needs four supporting pieces that ADR-0013..0018 do not name.
Each one serves a component already in the fixed stack and replaces none:

- The human approved the first three through the Phase 2 plan's open items
  P-2 and P-8 (2026-10-02). This ADR records that decision.
- Pillow was not on that list and was approved separately on 2026-10-04.

## Decision
- **`minio` Python SDK** is the MinIO client (plan P-2). Not `boto3`.
- **`pgvector` Python package** provides the SQLAlchemy `Vector` type for the
  `vector(1024)` column (plan P-8).
- **`minio/mc` Docker image** runs the one-shot `minio-init` compose service.
  That service creates the private bucket(s) and the scoped app credential
  required by ADR-0018 (plan P-2).
- **Pillow** handles page images for OCR (`app/integrations/ocr.py`) and the
  test fixtures that generate scanned PDFs. `pdfplumber` already depends on
  it.
- **numpy is not a direct dependency.** No application code imports it. It is
  still installed indirectly through `pgvector` and `sentence-transformers`.

## Consequences
- Later phases use these and do not introduce alternatives (for example
  `boto3`, or `pgvecto.rs`) without a new, human-approved ADR.
- This ADR does not open the door to other additions. Any further library or
  infrastructure still needs its own human decision.
