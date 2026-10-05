"""IngestionService - the deterministic ingestion pipeline (FR-CON-002, SRS
Section 17 and 33).

    VALIDATE -> EXTRACT -> OCR -> CLEAN -> CHUNK -> EMBED -> STORE

Hard rules (`.claude/rules/deterministic-services.md`, NFR-MNT-001):
- no LLM, no `app.agents`/`app.prompts` imports, no hidden global state;
- all I/O goes through injected ports (object store, OCR engine, tokenizer,
  embedder, repository), so the orchestration is unit-testable without
  network or database;
- the same file produces the same chunks (pure cleaning/unit/chunk stages).

Resume/idempotency (BUS-040, NFR-REL-001): extracted text is not persisted
(ADR-0018 keeps derived artifacts out of MinIO), so VALIDATE..CHUNK are
recomputed on retry *unless* a previous attempt already persisted the chunks
(CHUNK succeeded); then those stages are SKIPPED and only chunks still missing
an embedding are embedded. Re-running never duplicates chunks.
"""

from __future__ import annotations

import hashlib
import math
import os
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.core.errors import ValidationError
from app.services.ingestion import cleaning, mime
from app.services.ingestion.chunking import Chunk, chunk_blocks
from app.services.ingestion.errors import (
    EMPTY_EXTRACTION_MESSAGE,
    IngestionFailure,
    IngestionSkip,
    TransientIngestionError,
    UnreadableDocumentError,
)
from app.services.ingestion.parsers.base import ParsedDocument, Segment, non_whitespace_chars, parse_document
from app.services.ingestion.ports import Embedder, ObjectStore, OcrEngine, Tokenizer
from app.services.ingestion.unit_boundaries import UnitRef, assign_units

VALIDATE, EXTRACT, OCR, CLEAN, CHUNK, EMBED, STORE = (
    "VALIDATE",
    "EXTRACT",
    "OCR",
    "CLEAN",
    "CHUNK",
    "EMBED",
    "STORE",
)
STAGES = (VALIDATE, EXTRACT, OCR, CLEAN, CHUNK, EMBED, STORE)
RETRY_MESSAGE = "Processing is incomplete and will retry. Current content is unchanged."  # Section 37
NO_UNIT_HEADINGS_MESSAGE = (
    "No Unit headings (for example 'Unit 1') matching this Subject's Units were found in the file. "
    "Add Unit headings, or upload it again for a single Unit."
)
_NORM_TOLERANCE = 1e-3


@dataclass(frozen=True)
class IngestionSettings:
    min_page_chars: int = 25
    render_dpi: int = 300
    ocr_min_mean_confidence: float = 60.0
    ocr_min_chars: int = 25
    blank_ink_ratio: float = 0.001
    include_pptx_notes: bool = True
    max_tokens: int = 800
    overlap_tokens: int = 120
    embed_batch_size: int = 16
    expected_dimension: int = 1024
    is_normalized: bool = True
    max_pdf_pages: int = 500
    archive_max_uncompressed_bytes: int = 200 * 1024 * 1024
    archive_max_compression_ratio: float = 100.0
    archive_max_members: int = 2000


@dataclass(frozen=True)
class IngestionContext:
    version_id: str
    subject_id: str
    chunk_type: str  # SYLLABUS | NOTES | PPT | PYQ | LAB
    ext: str
    source_file: str
    storage_key: str
    sha256: str
    size_bytes: int
    units: list[UnitRef]
    fixed_unit_no: int | None
    embedding_config_id: str


@dataclass(frozen=True)
class IngestionResult:
    status: str  # SUCCEEDED | FAILED | SKIPPED (another live worker already runs this version)
    failed_stage: str | None = None
    message: str | None = None
    chunk_count: int = 0


class IngestionRepository(Protocol):
    def begin_attempt(self, version_id: str) -> int:
        """Start a new attempt and return its number. Raises IngestionInProgress if another
        worker is running this version and is still active, or IngestionNotNeeded if the
        version already SUCCEEDED or is no longer DRAFT (no duplicate or late attempts)."""
        ...

    def stage_succeeded_before(self, version_id: str, stage: str) -> bool: ...

    def record_stage(
        self,
        version_id: str,
        stage: str,
        attempt: int,
        status: str,
        started_at: datetime,
        finished_at: datetime | None,
        detail: dict | None,
        error: str | None,
    ) -> None: ...

    def chunk_count(self, version_id: str) -> int: ...

    def delete_chunks(self, version_id: str) -> None: ...

    def insert_chunks(self, ctx: IngestionContext, chunks: Sequence[Chunk]) -> None: ...

    def chunks_missing_embeddings(self, version_id: str, limit: int) -> list[tuple[str, str]]: ...

    def set_embeddings(self, version_id: str, embeddings: dict[str, list[float]]) -> None: ...

    def count_missing_embeddings(self, version_id: str) -> int: ...

    def finalize_success(self, version_id: str, embedding_config_id: str) -> None: ...

    def finalize_failure(self, version_id: str, stage: str, message: str) -> None: ...


@dataclass
class _Run:
    ctx: IngestionContext
    repo: IngestionRepository
    attempt: int
    now: Callable[[], datetime]
    stage_details: dict[str, dict] = field(default_factory=dict)
    current_stage: str = VALIDATE


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def _best_effort(write: Callable[[], None]) -> None:
    """Record a failure if possible; never replace the error being handled with a new one."""
    try:
        write()
    except Exception:  # noqa: BLE001, S110 - the caller re-raises the original error
        pass


def _stage(run: _Run, stage: str, fn: Callable[[], dict | None]) -> None:
    """Run one stage, recording start/finish/status (FR-CON-002 'each stage records
    success/failure'). Failures are re-raised as IngestionFailure for the caller."""
    run.current_stage = stage
    started = run.now()
    run.repo.record_stage(run.ctx.version_id, stage, run.attempt, "RUNNING", started, None, None, None)
    try:
        detail = fn() or {}
    except IngestionFailure as exc:
        run.repo.record_stage(
            run.ctx.version_id,
            stage,
            run.attempt,
            "FAILED",
            started,
            run.now(),
            exc.detail or None,
            exc.message,
        )
        raise
    except UnreadableDocumentError as exc:
        failure = IngestionFailure(stage, str(exc))
        run.repo.record_stage(
            run.ctx.version_id, stage, run.attempt, "FAILED", started, run.now(), None, failure.message
        )
        raise failure from exc
    except Exception as exc:
        # Best effort: the original error (e.g. a worker time-limit signal raised mid-write)
        # must stay the cause, even if recording the failure itself fails (finding N3).
        _best_effort(
            lambda: run.repo.record_stage(
                run.ctx.version_id, stage, run.attempt, "FAILED", started, run.now(), None, RETRY_MESSAGE
            )
        )
        raise TransientIngestionError(RETRY_MESSAGE) from exc
    run.stage_details[stage] = detail
    run.repo.record_stage(
        run.ctx.version_id, stage, run.attempt, "SUCCEEDED", started, run.now(), detail, None
    )


def _skip(run: _Run, stage: str, reason: str) -> None:
    now = run.now()
    run.repo.record_stage(
        run.ctx.version_id, stage, run.attempt, "SKIPPED", now, now, {"reason": reason}, None
    )


def _extract_text_total(segments: Sequence[Segment]) -> int:
    return sum(non_whitespace_chars(s.text) for s in segments)


def run_ingestion(
    ctx: IngestionContext,
    *,
    repo: IngestionRepository,
    store: ObjectStore,
    ocr: OcrEngine,
    tokenizer: Tokenizer,
    embedder: Embedder,
    settings: IngestionSettings,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> IngestionResult:
    try:
        attempt = repo.begin_attempt(ctx.version_id)
    except IngestionSkip as exc:  # already running elsewhere, or already done (m1, N2)
        return IngestionResult("SKIPPED", message=str(exc))
    run = _Run(ctx=ctx, repo=repo, attempt=attempt, now=now)
    try:
        resumed = repo.stage_succeeded_before(ctx.version_id, CHUNK) and repo.chunk_count(ctx.version_id) > 0
        if resumed:
            for st in (VALIDATE, EXTRACT, OCR, CLEAN, CHUNK):
                _skip(run, st, "chunks persisted by an earlier attempt")
        else:
            _run_text_pipeline(run, store, ocr, tokenizer, settings)
        _stage(run, EMBED, lambda: _embed_missing(run, embedder, settings))
        _stage(run, STORE, lambda: _finalize(run, store))
    except IngestionFailure as exc:
        repo.finalize_failure(ctx.version_id, exc.stage, exc.message)
        return IngestionResult("FAILED", exc.stage, exc.message)
    except TransientIngestionError as exc:
        _best_effort(lambda: repo.finalize_failure(ctx.version_id, run.current_stage, RETRY_MESSAGE))
        raise exc
    return IngestionResult("SUCCEEDED", chunk_count=repo.chunk_count(ctx.version_id))


def _run_text_pipeline(
    run: _Run, store: ObjectStore, ocr: OcrEngine, tokenizer: Tokenizer, cfg: IngestionSettings
) -> None:
    ctx = run.ctx
    holder: dict[str, object] = {}
    tmpdir = tempfile.mkdtemp(prefix="ingest_")
    path = os.path.join(tmpdir, f"original.{ctx.ext}")
    try:

        def validate() -> dict:
            store.download_to(ctx.storage_key, path)
            size = os.path.getsize(path)
            if size != ctx.size_bytes or _sha256_file(path) != ctx.sha256:
                raise IngestionFailure(
                    VALIDATE, "Stored file failed its integrity check (size/SHA-256 mismatch)."
                )
            if ctx.ext in ("pptx", "docx"):
                try:
                    mime.check_archive_limits(
                        path,
                        max_uncompressed_bytes=cfg.archive_max_uncompressed_bytes,
                        max_compression_ratio=cfg.archive_max_compression_ratio,
                        max_members=cfg.archive_max_members,
                    )
                except ValidationError as exc:
                    raise IngestionFailure(VALIDATE, str(exc)) from exc
            holder["doc"] = parse_document(
                path,
                ctx.ext,
                min_page_chars=cfg.min_page_chars,
                render_dpi=cfg.render_dpi,
                include_pptx_notes=cfg.include_pptx_notes,
                max_pdf_pages=cfg.max_pdf_pages,
            )
            return {"size_bytes": size, "sha256": ctx.sha256, "format": ctx.ext}

        _stage(run, VALIDATE, validate)
        doc: ParsedDocument = holder["doc"]  # type: ignore[assignment]

        def extract() -> dict:
            pending = [s.page_no for s in doc.segments if s.needs_ocr]
            if not doc.segments or (_extract_text_total(doc.segments) == 0 and not pending):
                raise IngestionFailure(EXTRACT, EMPTY_EXTRACTION_MESSAGE)
            return {"segments": len(doc.segments), "pages_needing_ocr": pending}

        _stage(run, EXTRACT, extract)

        def run_ocr() -> dict:
            candidates = [s for s in doc.segments if s.needs_ocr]
            if not candidates:
                return {"pages_ocr": 0}
            if doc.render_png is None:
                raise IngestionFailure(OCR, EMPTY_EXTRACTION_MESSAGE)
            replaced: dict[int, Segment] = {}
            failed: list[dict] = []
            blank: list[int] = []
            ocr_pages: list[int] = []
            engine_info: dict[str, str] = {}
            for seg in candidates:
                page_no = seg.page_no or 0
                png = doc.render_png(page_no)
                if ocr.is_blank(png, cfg.blank_ink_ratio):
                    blank.append(page_no)
                    replaced[page_no] = Segment(seg.text, seg.locator, seg.page_no, needs_ocr=False)
                    continue
                result = ocr.ocr_png(png)
                engine_info = {"engine_version": result.engine_version, "config": result.config}
                chars = non_whitespace_chars(result.text)
                if chars < cfg.ocr_min_chars or result.mean_confidence < cfg.ocr_min_mean_confidence:
                    failed.append(
                        {"page": page_no, "chars": chars, "mean_confidence": round(result.mean_confidence, 1)}
                    )
                    continue
                ocr_pages.append(page_no)
                replaced[page_no] = Segment(result.text, seg.locator, seg.page_no, needs_ocr=False)
            if failed:
                pages = ", ".join(str(f["page"]) for f in failed)
                raise IngestionFailure(
                    OCR,
                    f"OCR could not read page(s) {pages} of '{ctx.source_file}'. {EMPTY_EXTRACTION_MESSAGE}",
                    {"failed_pages": failed, **engine_info},
                )
            doc.segments[:] = [replaced.get(s.page_no or -1, s) if s.needs_ocr else s for s in doc.segments]
            if _extract_text_total(doc.segments) == 0:
                raise IngestionFailure(OCR, EMPTY_EXTRACTION_MESSAGE, {"blank_pages": blank, **engine_info})
            return {
                "pages_ocr": len(ocr_pages),
                "ocr_pages": ocr_pages,
                "blank_pages_skipped": blank,
                **engine_info,
            }

        _stage(run, OCR, run_ocr)

        def clean() -> dict:
            cleaned = cleaning.clean_segments(doc.segments)
            if not cleaned or _extract_text_total(cleaned) == 0:
                raise IngestionFailure(CLEAN, EMPTY_EXTRACTION_MESSAGE)
            holder["segments"] = cleaned
            return {"segments_before": len(doc.segments), "segments_after": len(cleaned)}

        _stage(run, CLEAN, clean)

        def chunk() -> dict:
            blocks, report = assign_units(
                holder["segments"],  # type: ignore[arg-type]
                units=ctx.units,
                fixed_unit_no=ctx.fixed_unit_no,
            )
            # No fixed Unit means "all Units" (a syllabus, or an explicit "All units" upload):
            # Units must come from headings (human decision 2026-10-04, finding m2).
            if ctx.fixed_unit_no is None and report.headings_matched == 0:
                raise IngestionFailure(CHUNK, NO_UNIT_HEADINGS_MESSAGE)
            chunks = chunk_blocks(blocks, tokenizer, max_tokens=cfg.max_tokens, overlap=cfg.overlap_tokens)
            if not chunks:
                raise IngestionFailure(CHUNK, EMPTY_EXTRACTION_MESSAGE)
            run.repo.delete_chunks(ctx.version_id)  # idempotent: replace any partial earlier attempt
            run.repo.insert_chunks(ctx, chunks)
            return {
                "chunks": len(chunks),
                "unit_headings_matched": report.headings_matched,
                "unit_headings_ignored": report.ignored_headings,
                "unresolved_unit_blocks": report.unresolved_blocks,
                "max_tokens": cfg.max_tokens,
                "overlap_tokens": cfg.overlap_tokens,
            }

        _stage(run, CHUNK, chunk)
    finally:
        doc_obj = holder.get("doc")
        if isinstance(doc_obj, ParsedDocument):
            doc_obj.close()
        try:
            if os.path.exists(path):
                os.remove(path)
            os.rmdir(tmpdir)
        except OSError:
            pass


def _valid_vector(vec: Sequence[float], dimension: int, normalized: bool) -> bool:
    if len(vec) != dimension or not all(math.isfinite(x) for x in vec):
        return False
    if normalized:
        norm = math.sqrt(sum(x * x for x in vec))
        return abs(norm - 1.0) <= _NORM_TOLERANCE
    return True


def _embed_missing(run: _Run, embedder: Embedder, cfg: IngestionSettings) -> dict:
    total = 0
    while True:
        batch = run.repo.chunks_missing_embeddings(run.ctx.version_id, cfg.embed_batch_size)
        if not batch:
            break
        ids = [cid for cid, _ in batch]
        vectors = embedder.embed([text for _, text in batch])
        if len(vectors) != len(ids):
            raise IngestionFailure(EMBED, "The embedding model returned the wrong number of vectors.")
        for vec in vectors:
            if not _valid_vector(vec, cfg.expected_dimension, cfg.is_normalized):
                raise IngestionFailure(
                    EMBED,
                    f"Embedding failed validation (expected {cfg.expected_dimension} "
                    "finite normalized values).",
                )
        run.repo.set_embeddings(run.ctx.version_id, dict(zip(ids, vectors, strict=True)))
        total += len(ids)
    return {"embedded_chunks": total, "embedding_config_id": run.ctx.embedding_config_id}


def _finalize(run: _Run, store: ObjectStore) -> dict:
    if not store.exists(run.ctx.storage_key):
        raise IngestionFailure(STORE, "The stored original file is missing from object storage.")
    count = run.repo.chunk_count(run.ctx.version_id)
    if count == 0 or run.repo.count_missing_embeddings(run.ctx.version_id) > 0:
        raise IngestionFailure(STORE, "Ingestion produced no complete embedded chunks.")
    run.repo.finalize_success(run.ctx.version_id, run.ctx.embedding_config_id)
    return {"chunks": count}
