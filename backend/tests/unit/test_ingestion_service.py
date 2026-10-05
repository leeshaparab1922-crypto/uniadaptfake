"""IngestionService orchestration (FR-CON-002, AC-004, BUS-040) with fake ports - no services."""

from __future__ import annotations

import pytest

from app.services.ingestion.errors import EMPTY_EXTRACTION_MESSAGE, TransientIngestionError
from app.services.ingestion.ports import OcrResult
from app.services.ingestion.unit_boundaries import UnitRef
from app.services.ingestion_service import (
    NO_UNIT_HEADINGS_MESSAGE,
    STAGES,
    IngestionContext,
    IngestionSettings,
    run_ingestion,
)
from tests.support import docs
from tests.support.fakes import FakeEmbedder, FakeObjectStore, FakeOcr, FakeTokenizer, InMemoryRepo, put_file

UNITS = [UnitRef(1, "Basics"), UnitRef(2, "Trees"), UnitRef(3, "Graphs")]
CFG = IngestionSettings(render_dpi=72)
GOOD_OCR = OcrResult(
    "Unit 1 Basics\nArrays and lists are covered here in detail.", 91.0, "tesseract 5.3.0", "--oem 1 --psm 3"
)


def make(data: bytes, ext: str, *, chunk_type="NOTES", fixed_unit=1, units=UNITS):
    store = FakeObjectStore()
    key = f"subjects/s/assets/a/versions/v/original.{ext}"
    sha = put_file(store, key, data)
    ctx = IngestionContext(
        version_id="v1",
        subject_id="s1",
        chunk_type=chunk_type,
        ext=ext,
        source_file=f"file.{ext}",
        storage_key=key,
        sha256=sha,
        size_bytes=len(data),
        units=list(units),
        fixed_unit_no=fixed_unit,
        embedding_config_id="cfg1",
    )
    return ctx, store


def run(ctx, store, repo=None, *, ocr=None, embedder=None, cfg=CFG):
    repo = repo or InMemoryRepo()
    result = run_ingestion(
        ctx,
        repo=repo,
        store=store,
        ocr=ocr or FakeOcr(),
        tokenizer=FakeTokenizer(),
        embedder=embedder or FakeEmbedder(),
        settings=cfg,
    )
    return result, repo


TEXT = "Arrays store elements contiguously. " * 30


def test_happy_path_runs_every_stage_in_order_and_succeeds():
    ctx, store = make(docs.make_txt(TEXT), "txt")
    result, repo = run(ctx, store)
    assert result.status == "SUCCEEDED" and result.chunk_count == len(repo.chunks) > 0
    assert repo.stages(1) == [(s, "SUCCEEDED") for s in STAGES]
    assert repo.status == "SUCCEEDED" and repo.embedding_config_id == "cfg1"
    assert all(c["embedding"] is not None for c in repo.chunks)


def test_every_stage_records_start_finish_status():
    ctx, store = make(docs.make_txt(TEXT), "txt")
    _, repo = run(ctx, store)
    for r in repo.stage_runs:
        assert r["started_at"] is not None and r["finished_at"] is not None and r["attempt"] == 1
    chunk_stage = next(r for r in repo.stage_runs if r["stage"] == "CHUNK")
    assert chunk_stage["detail"]["chunks"] == len(repo.chunks)
    assert chunk_stage["detail"]["max_tokens"] == 800 and chunk_stage["detail"]["overlap_tokens"] == 120


def test_integrity_mismatch_fails_validate_stage():
    ctx, store = make(docs.make_txt(TEXT), "txt")
    store.objects[ctx.storage_key] = b"tampered content"
    result, repo = run(ctx, store)
    assert result.status == "FAILED" and result.failed_stage == "VALIDATE"
    assert repo.stages(1)[0] == ("VALIDATE", "FAILED") and repo.chunks == []


def test_corrupt_document_fails_validate_clearly():
    ctx, store = make(b"%PDF-1.4 garbage", "pdf")
    result, repo = run(ctx, store)
    assert (result.status, result.failed_stage) == ("FAILED", "VALIDATE")
    assert "could not be read" in result.message and repo.status == "FAILED"


def test_empty_extraction_fails_asset_no_chunks_created():
    ctx, store = make(b"   \n\n  ", "txt")
    result, repo = run(ctx, store)
    assert (result.status, result.failed_stage, result.message) == (
        "FAILED",
        "EXTRACT",
        EMPTY_EXTRACTION_MESSAGE,
    )
    assert repo.chunks == [] and repo.failure_message == EMPTY_EXTRACTION_MESSAGE


def test_failure_stops_later_stages_from_running():
    ctx, store = make(b"  ", "txt")
    _, repo = run(ctx, store)
    assert [s for s, _ in repo.stages(1)] == ["VALIDATE", "EXTRACT"]


def test_scanned_pdf_pages_are_ocred_and_become_chunks():
    ctx, store = make(docs.make_scanned_pdf(["x", "y"]), "pdf", fixed_unit=None, chunk_type="SYLLABUS")
    ocr = FakeOcr(lambda png: GOOD_OCR)
    result, repo = run(ctx, store, ocr=ocr)
    assert result.status == "SUCCEEDED" and ocr.calls == 2
    ocr_stage = next(r for r in repo.stage_runs if r["stage"] == "OCR")
    assert ocr_stage["detail"]["ocr_pages"] == [1, 2]
    assert (
        ocr_stage["detail"]["engine_version"] == "tesseract 5.3.0"
        and "psm 3" in ocr_stage["detail"]["config"]
    )
    assert repo.chunks[0]["chunk"].unit_no == 1  # heading detected in OCR text


def test_ocr_failure_names_asset_and_page_and_creates_no_chunks():
    ctx, store = make(docs.make_scanned_pdf(["a", "b", "c"]), "pdf")
    outcomes = [GOOD_OCR, OcrResult("jjj", 20.0, "t", "c"), GOOD_OCR]
    result, repo = run(ctx, store, ocr=FakeOcr(outcomes))
    assert (result.status, result.failed_stage) == ("FAILED", "OCR")
    assert "page(s) 2" in result.message and "file.pdf" in result.message
    assert repo.chunks == []
    assert next(r for r in repo.stage_runs if r["stage"] == "OCR")["detail"]["failed_pages"][0]["page"] == 2


def test_low_confidence_page_fails_even_with_enough_characters():
    ctx, store = make(docs.make_scanned_pdf(["a"]), "pdf")
    low = OcrResult("x" * 200, 59.9, "t", "c")
    result, _ = run(ctx, store, ocr=FakeOcr([low]))
    assert result.failed_stage == "OCR"


def test_confidence_exactly_at_threshold_passes():
    ctx, store = make(docs.make_scanned_pdf(["a"]), "pdf")
    ok = OcrResult("Unit 1 " + "word " * 20, 60.0, "t", "c")
    result, _ = run(ctx, store, ocr=FakeOcr([ok]))
    assert result.status == "SUCCEEDED"


def test_blank_pages_are_skipped_not_failed():
    ctx, store = make(docs.make_scanned_pdf(["a", None]), "pdf")
    ocr = FakeOcr([GOOD_OCR], blank=lambda png: ocr.calls >= 1)
    result, repo = run(ctx, store, ocr=ocr)
    assert result.status == "SUCCEEDED"
    detail = next(r for r in repo.stage_runs if r["stage"] == "OCR")["detail"]
    assert detail["blank_pages_skipped"] == [2] and detail["ocr_pages"] == [1]


def test_all_pages_blank_is_an_empty_extraction_failure():
    ctx, store = make(docs.make_scanned_pdf([None, None]), "pdf")
    result, repo = run(ctx, store, ocr=FakeOcr(blank=lambda png: True))
    assert (result.failed_stage, result.message) == ("OCR", EMPTY_EXTRACTION_MESSAGE) and repo.chunks == []


def test_syllabus_without_unit_headings_fails_at_chunk():
    ctx, store = make(
        docs.make_txt("Just prose without headings. " * 20), "txt", chunk_type="SYLLABUS", fixed_unit=None
    )
    result, repo = run(ctx, store)
    assert (result.failed_stage, result.message) == ("CHUNK", NO_UNIT_HEADINGS_MESSAGE) and repo.chunks == []


def test_syllabus_chunks_follow_unit_headings():
    text = "Unit 1: Basics\n" + "alpha " * 50 + "\n\nUnit 2: Trees\n" + "beta " * 50
    ctx, store = make(docs.make_txt(text), "txt", chunk_type="SYLLABUS", fixed_unit=None)
    result, repo = run(ctx, store)
    assert result.status == "SUCCEEDED"
    assert [c["chunk"].unit_no for c in repo.chunks] == [1, 2]
    assert all("beta" not in c["chunk"].text for c in repo.chunks if c["chunk"].unit_no == 1)


def test_wrong_dimension_embedding_fails_stage():
    ctx, store = make(docs.make_txt(TEXT), "txt")
    result, repo = run(ctx, store, embedder=FakeEmbedder(wrong_dimension=768))
    assert (result.status, result.failed_stage) == ("FAILED", "EMBED") and repo.status == "FAILED"


def test_non_normalized_embedding_rejected():
    class Raw(FakeEmbedder):
        def embed(self, texts):
            return [[2.0] + [0.0] * 1023 for _ in texts]

    ctx, store = make(docs.make_txt(TEXT), "txt")
    result, _ = run(ctx, store, embedder=Raw())
    assert result.failed_stage == "EMBED"


def test_embedder_crash_is_transient_and_resume_embeds_only_missing_chunks():
    text = "word " * 2500  # several chunks
    ctx, store = make(docs.make_txt(text), "txt")
    repo = InMemoryRepo()
    flaky = FakeEmbedder(fail_on_call=2)
    cfg = IngestionSettings(render_dpi=72, embed_batch_size=2)
    with pytest.raises(TransientIngestionError):
        run(ctx, store, repo, embedder=flaky, cfg=cfg)
    assert repo.status == "FAILED" and "will retry" in repo.failure_message
    done_before = sum(1 for c in repo.chunks if c["embedding"] is not None)
    n_chunks = len(repo.chunks)
    assert 0 < done_before < n_chunks

    good = FakeEmbedder()
    result, repo = run(ctx, store, repo, embedder=good, cfg=cfg)
    assert result.status == "SUCCEEDED" and len(repo.chunks) == n_chunks  # no duplicates
    assert len(good.embedded_texts) == n_chunks - done_before  # only the missing ones


def test_resume_skips_succeeded_stages():
    text = "word " * 2500
    ctx, store = make(docs.make_txt(text), "txt")
    repo = InMemoryRepo()
    with pytest.raises(TransientIngestionError):
        run(ctx, store, repo, embedder=FakeEmbedder(fail_on_call=1))
    run(ctx, store, repo)
    attempt2 = dict(repo.stages(2))
    assert [attempt2[s] for s in ("VALIDATE", "EXTRACT", "OCR", "CLEAN", "CHUNK")] == ["SKIPPED"] * 5
    assert attempt2["EMBED"] == attempt2["STORE"] == "SUCCEEDED"


def test_rerun_is_idempotent_no_duplicate_chunks():
    ctx, store = make(docs.make_txt(TEXT), "txt")
    repo = InMemoryRepo()
    first, _ = run(ctx, store, repo)
    snapshot = [(c["id"], c["chunk"].text) for c in repo.chunks]
    second, _ = run(ctx, store, repo)
    assert first.chunk_count == second.chunk_count
    assert [(c["id"], c["chunk"].text) for c in repo.chunks] == snapshot


def test_failed_chunk_stage_replaces_partial_chunks_on_retry():
    ctx, store = make(docs.make_txt(TEXT), "txt")
    repo = InMemoryRepo()
    repo.insert_chunks(ctx, [])  # no-op; simulate leftovers from a crashed CHUNK stage
    repo.chunks.append(dict(id="stale", index=0, chunk=object(), embedding=None))
    result, repo = run(ctx, store, repo)
    assert result.status == "SUCCEEDED" and all(c["id"] != "stale" for c in repo.chunks)


def test_pipeline_is_deterministic_for_identical_input():
    ctx, store = make(docs.make_txt(TEXT * 5), "txt")
    _, a = run(ctx, store)
    _, b = run(ctx, store)
    assert [c["chunk"] for c in a.chunks] == [c["chunk"] for c in b.chunks]


def test_missing_stored_object_fails_store_stage_not_success():
    ctx, store = make(docs.make_txt(TEXT), "txt")

    class Vanishing(FakeObjectStore):
        def exists(self, key):
            return False

    vanishing = Vanishing()
    vanishing.objects = store.objects
    result, repo = run(ctx, vanishing)
    assert (result.status, result.failed_stage) == ("FAILED", "STORE") and repo.status == "FAILED"


def test_ingestion_modules_never_import_llm_or_prompt_code():
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[2] / "app"
    files = [root / "services" / "ingestion_service.py", *(root / "services" / "ingestion").rglob("*.py")]
    pattern = re.compile(
        r"^\s*(?:from|import)\s+(?:langchain|langgraph|anthropic|openai|app\.agents|app\.prompts)", re.M
    )
    offenders = [str(f) for f in files if pattern.search(f.read_text(encoding="utf-8"))]
    assert offenders == []


# ---------------------------------------------------------------- fixes after the 2A verification


def test_all_units_notes_upload_without_headings_fails_at_chunk():
    """Finding m2 (human decision 2026-10-04): no fixed Unit means "All units" for every
    content type, so Units must come from headings."""
    ctx, store = make(
        docs.make_txt("Prose without headings. " * 20), "txt", chunk_type="NOTES", fixed_unit=None
    )
    result, repo = run(ctx, store)
    assert (result.failed_stage, result.message) == ("CHUNK", NO_UNIT_HEADINGS_MESSAGE) and repo.chunks == []


def test_all_units_notes_upload_with_headings_splits_by_unit():
    text = "Unit 1: Basics\n" + "alpha " * 40 + "\n\nUnit 3: Graphs\n" + "gamma " * 40
    ctx, store = make(docs.make_txt(text), "txt", chunk_type="NOTES", fixed_unit=None)
    result, repo = run(ctx, store)
    assert result.status == "SUCCEEDED"
    assert [c["chunk"].unit_no for c in repo.chunks] == [1, 3]


def test_archive_over_the_limits_fails_at_validate():
    """Finding M5: zip-bomb limits are re-checked in the pipeline, not only at upload."""
    ctx, store = make(docs.make_docx([("Heading 1", "Unit 1"), ("Normal", "text")]), "docx")
    tight = IngestionSettings(render_dpi=72, archive_max_members=2)
    result, repo = run(ctx, store, cfg=tight)
    assert result.status == "FAILED" and result.failed_stage == "VALIDATE"
    assert "too many parts" in (result.message or "") and repo.chunks == []


def test_pdf_over_the_page_cap_fails_at_validate():
    ctx, store = make(docs.make_text_pdf([["Unit 1 text " * 5], ["more"], ["more"]]), "pdf")
    result, _ = run(ctx, store, cfg=IngestionSettings(render_dpi=72, max_pdf_pages=2))
    assert result.status == "FAILED" and result.failed_stage == "VALIDATE"
    assert "the limit is 2" in (result.message or "")


def test_duplicate_delivery_while_another_worker_runs_is_skipped():
    """Finding m1: begin_attempt refuses a second live run; the pipeline does nothing."""
    from app.services.ingestion.errors import IngestionInProgress

    class BusyRepo(InMemoryRepo):
        def begin_attempt(self, version_id: str) -> int:
            raise IngestionInProgress("already running")

    ctx, store = make(docs.make_txt("Unit 1\nsome text here"), "txt")
    repo = BusyRepo()
    result, _ = run(ctx, store, repo=repo)
    assert result.status == "SKIPPED" and repo.stage_runs == [] and repo.chunks == []


def test_late_duplicate_delivery_of_a_finished_version_is_skipped():
    """Finding N2: begin_attempt refuses a version that already SUCCEEDED or is not DRAFT."""
    from app.services.ingestion.errors import IngestionNotNeeded

    class DoneRepo(InMemoryRepo):
        def begin_attempt(self, version_id: str) -> int:
            raise IngestionNotNeeded("already ingested")

    ctx, store = make(docs.make_txt("Unit 1\nsome text here"), "txt")
    repo = DoneRepo()
    result, _ = run(ctx, store, repo=repo)
    assert result.status == "SKIPPED" and repo.stage_runs == []


def test_failure_recording_errors_do_not_replace_the_original_error():
    """Finding N3: if writing the FAILED record itself fails, the original error stays the cause."""

    class FlakyRepo(InMemoryRepo):
        def record_stage(self, version_id, stage, attempt, status, *args):
            if status == "FAILED":
                raise RuntimeError("database is gone")
            return super().record_stage(version_id, stage, attempt, status, *args)

        def finalize_failure(self, version_id, stage, message):
            raise RuntimeError("database is gone")

    class ExplodingEmbedder(FakeEmbedder):
        def embed(self, texts):
            raise KeyError("original problem")

    ctx, store = make(docs.make_txt("Unit 1\n" + "alpha " * 30), "txt")
    with pytest.raises(TransientIngestionError) as info:
        run(ctx, store, repo=FlakyRepo(), embedder=ExplodingEmbedder())
    assert isinstance(info.value.__cause__, KeyError)
