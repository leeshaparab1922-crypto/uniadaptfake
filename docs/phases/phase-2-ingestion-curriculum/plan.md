# Phase 2 — Ingestion & Curriculum — Implementation Plan

Status: APPROVED. Slice 2A accepted 2026-10-04; slice 2B approved 2026-10-04 and implemented 2026-10-04. Neither slice's Docker-backed tests (pg/minio/tesseract/hf_model) have been run: no Docker on the implementing machine. See "2A: As-built record", "2B: As-built record" and "Approval" below.
Branch: `phase-2-ingestion-curriculum` (from `phase-1-foundation`).
Delivery shape: two slices, **2A Ingestion** then **2B Curriculum**. Each slice has its own file list, its own Alembic migration, and its own tests. 2B cannot start until 2A is green. The slices ship together as one phase (phase-state.json has one status per phase); implementation commits are made per slice so the verifier can review them separately.

## Phase

- Phase number: 2
- Phase name: Ingestion & Curriculum
- SRS Section-43 row (verbatim):
  - Main Features: MinIO/OCR/chunks/embeddings, immutable shared versions, Subject Owner activation, Curriculum Agent, validation/editor/fallback
  - Requirements: FR-CON-001..004, FR-CUR-001..004
  - Dependencies: Phase 1 SubjectInstances/Teachers
  - Expected Demo: Feed cyclic syllabus; CO edits but cannot activate; Owner activates corrected graph; prior active chain remains resolvable.

## Slice dependency

```
Phase 1 (SubjectInstance, TeacherAssignment, SubjectOwnerAssignment, Subject, Unit, audit_logs)
        |
        v
Slice 2A  Ingestion   --- produces --->  ACTIVE syllabus ContentVersion (ingestion SUCCEEDED, chunks + vectors, embedding_config)
        |
        v
Slice 2B  Curriculum  --- requires --->  an ACTIVE syllabus ContentVersion for the Subject (FR-CUR-001 Pre)
                           also reuses ->  2A's embedder + embedding_configs (duplicate-Topic detection) and content_chunks (source refs)
```

2B migration `0003` has `down_revision = "0002"` (2A). 2A has no dependency on 2B.

## Requirements in Scope

Pulled with `srs-lookup` (FR rows verbatim in SRS Section 12, lines 324-331). Summary:

| ID | Type | Summary |
|---|---|---|
| FR-CON-001 | FR | Assigned Teacher uploads PDF/PPTX/DOCX/UTF-8 TXT (<=25 MB) or registers an HTTPS recommendation-only link; creates DRAFT version/resource; queues ingestion; active content unchanged. |
| FR-CON-002 | FR | Deterministic ingestion: validate, OCR scanned pages, clean, chunk (<=800 embedding-model tokens, 120 overlap, no Unit crossing), embed, store (MinIO + PostgreSQL + pgvector); per-stage record, retry/resume, empty extraction fails clearly; chunks retrievable only under correct subject/version/approval scope. |
| FR-CON-003 | FR | Each chunk stores `subject_id`, `content_version_id`, `unit_no`, `source_file`, page/slide/section locator, `chunk_type` (`syllabus|notes|ppt|pyq|lab`); AI outputs link to immutable chunk refs; links never create chunks. |
| FR-CON-004 | FR | Immutable-file DRAFT ContentVersion / DRAFT ApprovedResourceLink; only the Subject Owner activates/approves/rolls back; history and citations preserved; approved content never edited in place. |
| FR-CUR-001 | FR | Assigned Teacher requests generation; Curriculum Agent creates DRAFT Subject-level CurriculumVersion (stable Topic IDs, Units/Topics, outcomes, Bloom, hours, inherited Unit weightage, intra-/earlier-semester cross-subject prerequisite edges with confidence 0..1); validation runs; current ACTIVE stays available; invalid output fails safely. |
| FR-CUR-002 | FR | DFS cycle detection (drop+flag lowest-confidence edge, tie-break ascending normalized `(topic_id, prereq_topic_id)`, repeat until acyclic), orphan detection, duplicate-Topic detection (versioned config, initial `>0.92`); changed model/threshold cannot activate before validation. |
| FR-CUR-003 | FR | Assigned Teacher renames, merges, splits, reorders, classifies (`Core|Optional|Self-study`), changes hours, adds/deletes edges; each edit saves and reruns validation; stable IDs preserved/mapped; approval stays pending; no invalid graph approved. |
| FR-CUR-004 | FR | Subject Owner approves (activates) / rejects (draft RETURNED, prior ACTIVE unchanged) / explicitly activates flat Unit-order fallback when no ACTIVE exists; audited; atomic active-pointer update. |
| BUS-020 | BUS | Curriculum version needs explicit Owner approval to become ACTIVE; approved versions immutable. |
| BUS-021 | BUS | Cycle, orphan, duplicate detection run before approval (active versioned embedding config, initial `>0.92`). |
| BUS-022 | BUS | Lowest-confidence edge dropped and flagged per cycle (runtime unit-order fallback is Phase 7, not here). |
| BUS-023 | BUS | Owner rejection leaves prior ACTIVE unchanged; flat fallback only when no prior ACTIVE exists, explicitly by Owner. |
| BUS-039 | BUS | Upload creates immutable DRAFT version, never overwrites active content; only Owner activates/rolls back; existing chain stays usable until replacement activates. |
| BUS-040 | BUS | Ingestion/generation jobs retryable and resumable (idempotent Celery tasks). |
| BUS-043 | BUS | Any assigned Teacher (PRIMARY or CO) has full operations except final shared-artifact activation. |
| BUS-047 | BUS | HTTPS links are recommendation metadata only; never crawled, embedded, or used as evidence. |
| BUS-050 | BUS | Similarity thresholds stored with embedding-model version; revalidated before a new model version becomes active. |
| BUS-037 | BUS | AI outputs versioned, source-traceable, logged (`agent_runs`), minimized data to external AI. |
| BUS-042 | BUS | LAB-type Subjects support content upload (lab manuals) and coverage; exclusion from planning is Phase 7. No Phase 2 special-casing beyond allowing `lab` content. |
| AC-004 | AC | Scanned syllabus: OCR, <=800/120 chunks, vectors, source metadata, no Unit crossing. NEGATIVE: empty/unreadable extraction fails clearly; no empty approved chunks. |
| AC-005 | AC | v1 ACTIVE + Teacher uploads v2 => v1 stays ACTIVE, v2 DRAFT; Owner activates v2 => v1 SUPERSEDED but traceable. NEGATIVE: CO/unassigned Teacher activation or rollback rejected. |
| AC-006 | AC | A->B 0.8, B->A 0.4 => 0.4 edge dropped/flagged, acyclic; ties follow ascending IDs. NEGATIVE: orphan or remaining cycle blocks approval. |
| AC-007 | AC | Owner approves valid DRAFT => ACTIVE, prior traceable. NEGATIVE: CO approval or remaining cycle blocked; with no ACTIVE graph only explicit Owner flat fallback may activate. |
| NFR-SEC-009 | NFR | 25 MB, readability, declared-vs-actual MIME mismatch; HTTPS-only links; never crawled. |
| NFR-SEC-006/007/013 | NFR | Query-level scoping; least-privilege MinIO credential; no secrets in repo. |
| NFR-AI-001/002/004, NFR-MNT-001, NFR-DAT-002, NFR-REL-001, NFR-TST-001/002 | NFR | Strict schema + repair; agent_runs record; provider-neutral adapter; prompts in registry; versions resolvable; idempotent tasks; >=80% coverage on deterministic code; seed data + acceptance evidence. |
| Section 37 rows | Error handling | "OCR/empty extraction", "Partial background-job failure", "LLM/API outage", "Cyclic prerequisite graph", "Unauthorized access" messages reused verbatim. |

Sections 23/24/25 are NOT involved (see Exact-Algorithm Call-Outs).

## Dependencies Check

| Dependency | Satisfied? | Evidence |
|---|---|---|
| Phase 1 SubjectInstances | Yes | `backend/app/models/subject_instance.py` (`SubjectInstance`, status DRAFT/ACTIVE); `backend/alembic/versions/0001_initial_foundation_schema.py` creates `subject_instances`; routes `backend/app/api/routes/subject_instances.py`. |
| Phase 1 Teachers / assignments | Yes | `TeacherAssignment` (PRIMARY/CO) and `SubjectOwnerAssignment` (unique `subject_id`, ADR-0003) in the same model file and migration; `backend/app/services/assignment_service.py` (`set_subject_owner`). |
| Subject + Units for Unit boundaries / weightage | Yes | `backend/app/models/subject.py` (`Subject`, `Unit` with `order_index`, `weightage`); `subject_service` is the only Unit writer (ADR-0002); Phase 2 only reads Units. |
| Audit helper | Yes | `backend/app/services/audit.py::record` (ADR-0011). |
| Auth/CSRF/role guards | Yes | `backend/app/core/deps.py` (`require_role`, `csrf_protect`, `CurrentUser`). |

### State-file vs repo mismatches found (flagged, not silently ignored)

1. **No Dockerfiles exist in the repo.** `docker-compose.yml` has `build: ./backend` and `build: ./frontend` for `backend`, `celery`, `frontend`, but `git ls-files` shows no `Dockerfile`/`.dockerignore` anywhere. Phase 1 therefore never ran the stack through compose. Phase 2 needs a backend image (Tesseract, CPU-only torch), so slice 2A creates `backend/Dockerfile` and `backend/.dockerignore` (frontend Dockerfile is out of scope; flagged).
2. **Docker is not installed in the planning environment** (`docker: command not found`). Phase 1 used SQLite for exactly this reason (see `backend/tests/conftest.py` docstring). Phase 2's pgvector/MinIO tests cannot run in such an environment (see Risks R-1).
3. `phase-status` reports "deliverables found" for Phases 4 and 9; these are heuristic name-fragment false positives (no coverage/diagnostic/report code exists). State file is correct.
4. `docs/decisions/ADR-0013..0018` and the modified `docs/decisions/README.md` are **uncommitted** in the working tree; `frontend/tsconfig.tsbuildinfo` is an untracked build artifact (should be gitignored). Recommend committing the ADRs before implementation starts.
5. `app/workers/__init__.py` is empty but `docker-compose.yml` runs `celery -A app.workers worker`; slice 2A makes that command valid.
6. Teacher UI does not exist (`frontend/src/App.tsx` shows a placeholder for TEACHER); no `GET /teacher/subjects` endpoint exists yet.

## Conventions applied to both slices

- Routers: new files under `backend/app/api/routes/`, `dependencies=[Depends(csrf_protect), Depends(require_role(UserRole.TEACHER))]` (same pattern as `subjects.py`). Registered in `app/main.py`. Every endpoint has Pydantic request/response schemas.
- **Authorization model** (query-level, NFR-SEC-006/007):
  - "Assigned Teacher for Subject S" = holds a `TeacherAssignment` on any `SubjectInstance` of S. Not assigned => `404` non-enumerating (matches Phase 1 `teacher_service`, Section 37 allows `403` or non-enumerating `404`) and an audit/log line.
  - "Subject Owner of S" = `SubjectOwnerAssignment.owner_teacher_id == caller` (ADR-0003). Assigned but not Owner => `403 "Not authorized"` on owner-only actions.
- ADR-0011: every create/update/delete/decision in these slices calls `audit.record(...)` in the same transaction; service functions take `actor: User` explicitly.
- ADR-0009: all enums `VARCHAR + named CHECK` (`SAEnum(native_enum=False, create_constraint=True, length=N)`, constraint names `ck_<table>_<column>`).
- Domain errors reuse `app/core/errors.py` (`ValidationError` 400, `ForbiddenError` 403, `NotFoundError` 404, `ConflictError` 409). Phase 2 adds one new status mapping only if needed (`PayloadTooLarge` 413 for size: see Open Question P-12).
- ADR-0006: upload (C2) and generate (G1) endpoints use the existing `RateLimiter` with new configurable limits (`rate_limit_upload_per_teacher_per_window`, `rate_limit_generate_per_teacher_per_window`), not hard-coded.
- Deterministic boundary (`.claude/rules/deterministic-services.md`): `app/services/ingestion_service.py`, `app/services/ingestion/**`, and `app/services/curriculum_graph.py` never import `langchain*`, `anthropic`, `app.agents`, or `app.prompts`; enforced by a static import test (2B).

---

# SLICE 2A — INGESTION (FR-CON-001, FR-CON-002, FR-CON-003, FR-CON-004)

## 2A: Data model (SRS 31.2: ContentAsset/ContentVersion/ApprovedResourceLink/ContentChunk)

| Table | Key columns / constraints |
|---|---|
| `embedding_configs` | `id`, `model_id` ('BAAI/bge-m3'), `model_revision` (pinned commit sha), `tokenizer_revision` (same sha), `dimension` (CHECK = 1024), `normalized` bool, `max_chunk_tokens` (800), `chunk_overlap_tokens` (120), `created_at`; unique `(model_id, model_revision, dimension, normalized)`. ADR-0015 "embedding configuration version". |
| `content_assets` | `id`, `subject_id` FK, `content_type` (`SYLLABUS|NOTES|PPT|PYQ|LAB`, CHECK), `title`, `created_by` FK users, timestamps. **Partial unique index** `uq_one_syllabus_asset_per_subject (subject_id) WHERE content_type='SYLLABUS'` (assumption A-2). |
| `content_versions` | `id`, `content_asset_id` FK, `version_no` (unique per asset), `status` (`DRAFT|ACTIVE|SUPERSEDED`), `ingestion_status` (`PENDING|RUNNING|SUCCEEDED|FAILED`), `failed_stage`, `failure_message`, `unit_id` FK nullable, `storage_key` (unique), `original_filename`, `ext` (`pdf|pptx|docx|txt`), `mime_type`, `size_bytes` (CHECK 1..26214400), `sha256`, `embedding_config_id` FK nullable, `uploaded_by`, `activated_by`, `activated_at`, `supersedes_version_id` self-FK, timestamps. **Partial unique index** `uq_one_active_version_per_asset (content_asset_id) WHERE status='ACTIVE'`. CHECK: `status='ACTIVE'` implies `ingestion_status='SUCCEEDED'`. |
| `ingestion_stage_runs` | `id`, `content_version_id`, `stage` (`VALIDATE|EXTRACT|OCR|CLEAN|CHUNK|EMBED|STORE`), `attempt`, `status` (`RUNNING|SUCCEEDED|FAILED|SKIPPED`), `started_at`, `finished_at`, `detail` JSON (e.g. Tesseract version/config, failed page numbers, chunk count, embedding config id), `error`. Unique `(content_version_id, stage, attempt)`. Drives retry/resume and the UI stage timeline. |
| `content_chunks` | `id`, `subject_id`, `content_version_id` FK, `unit_no` int (nullable only when unit boundary unknown, see P-6), `source_file`, `locator_type` (`PAGE|SLIDE|SECTION|LINES`), `locator` text (e.g. `page:7`, `slide:3`, `section:Unit 2 > Trees#p14`, `lines:40-95`), `page_no` int nullable, `chunk_type` (`SYLLABUS|NOTES|PPT|PYQ|LAB`), `chunk_index` (unique per version), `text`, `token_count` (CHECK 1..800), `text_sha256`, `embedding vector(1024)`, `embedding_config_id` FK NOT NULL. CHECK: `locator` NOT NULL and non-empty (FR-CON-003 "mandatory locators cannot be null"). HNSW index `vector_cosine_ops`. Chunk rows are insert-only (no UPDATE path in code; test asserts). |
| `approved_resource_links` | `id`, `subject_id`, `topic_label` text nullable (P-11), `unit_id` nullable, `url` (CHECK `url LIKE 'https://%'`), `title`, `resource_type`, `est_minutes` (CHECK >0), `status` (`DRAFT|APPROVED|SUPERSEDED`), `uploaded_by`, `approved_by`, `approved_at`, `supersedes_link_id`. No embedding/chunk FK exists by design (BUS-047). |

All Phase 2 tables carry `Table.info={"pg_only": True}` so the SQLite fixtures skip them (see Test Infrastructure).

## 2A: Migration plan

`backend/alembic/versions/0002_ingestion_content_schema.py` (`down_revision = "0001"`):
- `CREATE EXTENSION IF NOT EXISTS vector` (pgvector/pgvector:pg15 image already ships it).
- Create the six tables above with named CHECKs (ADR-0009), both partial unique indexes, HNSW index on `content_chunks.embedding`.
- `downgrade()` drops in reverse order (extension left in place).
- Tested on real PostgreSQL: `0001 -> 0002 -> downgrade -> 0002` round trip (`test_migration_0002.py`).
- Seed row for `embedding_configs` is inserted by a script, not the migration, because the revision hash is an environment decision (P-9).

## 2A: Files to create

Backend source (33):
| Path | Purpose |
|---|---|
| `backend/alembic/versions/0002_ingestion_content_schema.py` | Migration above |
| `backend/app/models/content.py` | `ContentAsset`, `ContentVersion`, `IngestionStageRun`, `ContentChunk`, `ApprovedResourceLink` |
| `backend/app/models/embedding_config.py` | `EmbeddingConfig` |
| `backend/app/schemas/content.py` | Upload/response/list/stage/chunk/activate/rollback schemas |
| `backend/app/schemas/resource_link.py` | Link create/revise/approve schemas |
| `backend/app/api/routes/teacher_content.py` | Endpoints C1..C13 |
| `backend/app/services/content_service.py` | Authz helpers, upload orchestration (validate -> store -> register DRAFT -> enqueue), activate, rollback, retry; audit |
| `backend/app/services/resource_link_service.py` | Register/revise/approve links |
| `backend/app/services/content_retrieval.py` | Scope-filtered chunk retrieval (ACTIVE-only / by-version / by-id) used by later phases |
| `backend/app/services/ingestion_service.py` | **IngestionService** orchestrator: stage runner, idempotent resume, status transitions; pure over injected ports |
| `backend/app/services/ingestion/__init__.py` | Package |
| `backend/app/services/ingestion/ports.py` | `ObjectStore`, `OcrEngine`, `Embedder`, `Tokenizer` Protocols |
| `backend/app/services/ingestion/validators.py` | Extension allowlist, legacy/exe/image rejection, 25 MB, non-empty, HTTPS link rules |
| `backend/app/services/ingestion/mime.py` | Actual-MIME detection (library per P-1) + declared/actual mismatch check |
| `backend/app/services/ingestion/parsers/__init__.py`, `base.py` | `ParsedDocument`/`ParsedSegment` dataclasses, dispatch |
| `backend/app/services/ingestion/parsers/pdf.py` | pdfplumber text per page; pypdfium2 render at fixed DPI (ADR-0014) |
| `backend/app/services/ingestion/parsers/pptx.py` | python-pptx text frames/tables per slide (+ notes per P-5) |
| `backend/app/services/ingestion/parsers/docx.py` | python-docx paragraphs/headings/tables, section-path locator |
| `backend/app/services/ingestion/parsers/txt.py` | Strict UTF-8, `lines:a-b` locator |
| `backend/app/services/ingestion/cleaning.py` | Repeated header/footer removal, noise strip, boundaries retained, no meaning rewrite |
| `backend/app/services/ingestion/chunking.py` | <=800 tokens / 120 overlap, never across Unit boundary, shorter final chunk allowed |
| `backend/app/services/ingestion/unit_boundaries.py` | Unit assignment per P-6 |
| `backend/app/services/ingestion/locators.py` | Locator formatting/parsing/validation |
| `backend/app/integrations/__init__.py` | Package |
| `backend/app/integrations/object_store.py` | `MinioObjectStore` (write-once put, get, stat, key builder per ADR-0018, SDK per P-2) |
| `backend/app/integrations/ocr.py` | `TesseractOcrEngine` via pytesseract: `eng`, pinned config, per-page, returns text+confidence+version |
| `backend/app/integrations/embedding.py` | `BgeM3Embedder` (sentence-transformers, CPU, normalized, pinned revision) and test-safe `FakeEmbedder` in tests only |
| `backend/app/integrations/tokenizer.py` | `BgeM3Tokenizer` (AutoTokenizer, same revision) |
| `backend/app/workers/celery_app.py` | Celery app (Redis broker from config) |
| `backend/app/workers/ingestion_tasks.py` | `ingest_content_version(version_id)` idempotent, retry with backoff |
| `backend/scripts/bootstrap_minio.sh` | Idempotent: create `uniadapt-content`, private policy, scoped service key (uses `mc`, P-2) |
| `backend/scripts/seed_embedding_config.py` | Inserts the pinned `embedding_configs` row |
| `backend/scripts/seed_phase2_ingestion_demo.py` | Demo data: synthetic syllabus/notes via the service layer |

Infra/config (new, 6): `backend/Dockerfile` (python:3.11-slim, pinned `tesseract-ocr`/`tesseract-ocr-eng`, CPU-only torch wheel, HF cache volume path), `backend/.dockerignore`, `backend/scripts/test_services.sh` (compose up --wait, run pytest, optional down), `.github/workflows/backend-tests.yml` (CI that brings up compose services; file only, nothing is pushed), `backend/tests/fixtures/` generators (see tests), `docs/phases/phase-2-ingestion-curriculum/` (this plan).

## 2A: Files to change

| Path | Change |
|---|---|
| `backend/app/models/__init__.py` | Import `content`, `embedding_config` |
| `backend/app/main.py` | Register `teacher_content` router |
| `backend/app/core/config.py` | Add MinIO bucket + scoped credentials, upload limits, OCR/ingestion thresholds (values per P-4), embedding config, Celery/Redis, rate-limit knobs. Secrets only from env. |
| `backend/app/core/deps.py` | Add `get_object_store`, `get_ingestion_queue` dependency providers (overridable in tests) |
| `backend/app/workers/__init__.py` | Expose `celery_app` so `celery -A app.workers worker` works |
| `backend/pyproject.toml` | Add approved libs (P-8): `pytesseract`, `pdfplumber`, `pypdfium2`, `python-pptx`, `python-docx`, `sentence-transformers` (+`transformers`, CPU torch), `pgvector`, `celery`, MinIO client (P-2), MIME lib if any (P-1); pytest markers `pg`, `minio`, `tesseract`, `hf_model`; `--strict-markers` |
| `docker-compose.yml` | `minio` healthcheck; one-shot `minio-init` running `bootstrap_minio.sh`; HF-cache named volume on `backend` and `celery`; env wiring |
| `.env.example` | New keys (no real secrets): `MINIO_BUCKET`, `MINIO_APP_ACCESS_KEY/SECRET_KEY`, `EMBEDDING_MODEL_ID`, `EMBEDDING_MODEL_REVISION`, `HF_HOME`, OCR settings, `CELERY_BROKER_URL`, upload limits, test-service vars |
| `backend/tests/conftest.py` | Add Postgres/MinIO fixtures; SQLite `create_all` skips `info["pg_only"]` tables (details below) |
| `frontend/src/App.tsx` | Replace Teacher placeholder with `TeacherShell` |
| `.gitignore` | Add `frontend/tsconfig.tsbuildinfo` |

Frontend (2A):
| Path | Purpose |
|---|---|
| `frontend/src/types/content.ts` | Content/version/stage/chunk/link types |
| `frontend/src/api/contentApi.ts` | Calls for C1..C13 (multipart via existing `apiRequest(..., isFormData)`) |
| `frontend/src/components/TeacherShell.tsx` | Tabs: My Subjects, Content, (Curriculum added in 2B) |
| `frontend/src/pages/teacher/TeacherSubjects.tsx` | Assigned Subject picker with Owner badge |
| `frontend/src/pages/teacher/SubjectContent.tsx` | Assets/versions table with status badges |
| `frontend/src/pages/teacher/ContentUploadForm.tsx` | File + type + Unit + new-version-of-asset selector |
| `frontend/src/pages/teacher/IngestionStatus.tsx` | Stage timeline, failed stage/page message, Retry button |
| `frontend/src/pages/teacher/ChunkViewer.tsx` | Chunk list with metadata and locator, citation resolve |
| `frontend/src/pages/teacher/ResourceLinks.tsx` | Register/revise link, approve (Owner) |
| `frontend/src/pages/teacher/OwnerActions.tsx` | Activate / Rollback with reason (rendered only for Owner; server still enforces) |

## 2A: API endpoints

All under router prefix `/teacher`, role TEACHER, CSRF on mutations. "Assigned" and "Owner" as defined above.

| # | Method + Path | Guard | Purpose |
|---|---|---|---|
| C1 | `GET /teacher/subjects` | Assigned (lists only own) | Assigned Subjects with `is_owner`, Units |
| C2 | `POST /teacher/subjects/{subject_id}/content/uploads` (multipart: `file`, `content_type`, `unit_id?`, `content_asset_id?`, `title`) | Assigned; rate-limited | Validate, store, register DRAFT version, enqueue ingestion; returns 201 + version |
| C3 | `GET /teacher/subjects/{subject_id}/content/assets` | Assigned | Assets with versions, statuses, ingestion status |
| C4 | `GET /teacher/content/versions/{version_id}` | Assigned (via asset->subject) | Version detail + stage runs + failed stage/page |
| C5 | `POST /teacher/content/versions/{version_id}/retry` | Assigned | Resume failed/pending ingestion (idempotent) |
| C6 | `GET /teacher/content/versions/{version_id}/chunks?limit&offset` | Assigned | Chunk metadata list (no vectors) |
| C7 | `GET /teacher/content/chunks/{chunk_id}` | Assigned | Resolve immutable chunk ref to version, file, locator (any version status) |
| C8 | `POST /teacher/content/versions/{version_id}/activate` `{reason}` | **Owner** | DRAFT(SUCCEEDED) -> ACTIVE; prior ACTIVE -> SUPERSEDED; atomic; audit |
| C9 | `POST /teacher/content/assets/{asset_id}/rollback` `{target_version_id, reason}` | **Owner** | Reactivate a valid prior version; pointer-only; audit |
| C10 | `POST /teacher/subjects/{subject_id}/content/links` | Assigned | Register DRAFT HTTPS link; no fetch, no chunks |
| C11 | `GET /teacher/subjects/{subject_id}/content/links` | Assigned | List links + status |
| C12 | `POST /teacher/content/links/{link_id}/approve` `{reason}` | **Owner** | DRAFT -> APPROVED; audit |
| C13 | `POST /teacher/content/links/{link_id}/revisions` | Assigned | New DRAFT linked to prior (approved link never edited) |

No `PUT/PATCH/DELETE` exists on versions, chunks, or approved links (immutability). Background-only: Celery task `ingest_content_version` (no HTTP).

## 2A: Verb -> endpoint / UI / test traceability

Test IDs are `file::test_name` under `backend/tests/` (Vitest names under `frontend/src/__tests__/`). Markers: **U** = unit, no services; **PG** = Postgres+pgvector; **MN** = MinIO; **TS** = real Tesseract binary; **HF** = real bge-m3 model.

### FR-CON-001 Shared Subject Content Upload

| Verb (from FR) | API | UI | Named test(s) |
|---|---|---|---|
| upload file (PDF/PPTX/DOCX/TXT, <=25 MB) | C2 | `ContentUploadForm` file input + submit | `integration/test_content_api.py::test_upload_each_supported_type_creates_draft_pending` [PG,MN]; `unit/test_upload_validation.py::test_25mb_boundary_accepts_exact_and_rejects_plus_one` [U] |
| register link (HTTPS, recommendation-only) | C10 | `ResourceLinks` "Add link" form | `integration/test_content_api.py::test_register_https_link_creates_draft_no_chunks` [PG] |
| validate extension | C2 | inline form error toast | `unit/test_upload_validation.py::test_rejects_legacy_doc_ppt_exe_and_images` [U]; `test_content_api.py::test_upload_legacy_doc_rejected_400` [PG,MN] |
| validate actual MIME (declared vs actual) | C2 | error toast | `unit/test_mime_detection.py::test_declared_pdf_but_zip_content_rejected` (+7 siblings) [U]; `test_content_api.py::test_upload_mime_mismatch_rejected` [PG,MN] |
| validate size | C2 | error toast | `unit/test_upload_validation.py::test_oversize_rejected_before_full_buffering` [U] |
| validate non-empty content | C2 / C10 | error toast | `unit/test_upload_validation.py::test_zero_byte_file_rejected`; `test_blank_title_link_rejected` [U] |
| validate HTTPS | C10 | error toast | `unit/test_upload_validation.py::test_http_javascript_and_file_scheme_links_rejected` [U]; `test_content_api.py::test_register_http_link_rejected` [PG] |
| validate Subject assignment | C2/C10 | Subject picker lists only assigned (C1) | `test_content_api.py::test_unassigned_teacher_upload_rejected_404_no_data`; `::test_unassigned_teacher_link_rejected` [PG,MN] |
| register new DRAFT version/resource | C2/C10 | status badge "DRAFT" | `unit`-level: `integration/test_content_service.py::test_upload_creates_draft_version_with_sha_size_mime` [PG,MN] |
| not crawl / not embed links | C10 | none (nothing displayed) | `test_resource_link_service.py::test_link_registration_makes_no_network_call_and_no_chunk_rows` [PG] |
| queue ingestion (pending record) | C2 -> Celery | `IngestionStatus` shows "PENDING/queued" | `test_content_service.py::test_upload_enqueues_exactly_one_ingestion_task` [PG,MN] |
| active content unchanged | C2 | previous ACTIVE badge unchanged in list | `test_content_service.py::test_upload_v2_leaves_v1_active_and_intact` [PG,MN] (AC-005 positive) |

### FR-CON-002 Deterministic Ingestion

| Verb | API | UI | Named test(s) |
|---|---|---|---|
| validate (readability) | worker stage VALIDATE | stage timeline row "Validate" | `unit/test_parsers_*.py::test_corrupt_file_unreadable_error` x4 [U] |
| OCR scanned pages | worker stage OCR (no HTTP) | **No dedicated UI**; user sees ingestion status timeline "OCR: n pages" and, on failure, "OCR failed on page N" | `unit/test_ocr_adapter.py::test_page_without_text_triggers_ocr`, `::test_ocr_failure_names_asset_and_page` [U]; `integration/test_ocr_tesseract.py::test_scanned_pdf_ocr_text_extracted` [TS]; `::test_ocr_output_deterministic_across_runs` [TS] |
| clean | worker stage CLEAN | timeline row "Clean" | `unit/test_cleaning.py::test_repeated_header_footer_removed_page_boundaries_kept` (+7) [U] |
| chunk (<=800 tokens, 120 overlap, no Unit crossing, final shorter ok) | worker stage CHUNK | timeline "Chunk: N chunks"; `ChunkViewer` shows token_count | `unit/test_chunking.py::test_chunks_never_exceed_800_tokens`, `::test_overlap_is_exactly_120_tokens`, `::test_never_crosses_unit_boundary`, `::test_final_short_chunk_allowed`, `::test_chunking_is_deterministic` (+9) [U]; `integration/test_ingestion_e2e.py::test_ac004_scanned_syllabus_chunked_and_traceable` [PG,MN] |
| embed | worker stage EMBED | timeline "Embed" with model id/revision | `unit/test_ingestion_service.py::test_wrong_dimension_embedding_fails_stage`; `integration/test_embedding_hf.py::test_bge_m3_dim_1024_normalized_and_800_token_chunk_not_truncated` [HF] |
| store (MinIO + PostgreSQL + pgvector) | C2 (MinIO write), worker STORE | `ChunkViewer` lists stored chunks | `integration/test_minio_store.py::*` [MN]; `integration/test_chunk_store.py::test_vector_1024_roundtrip_and_cosine_order` [PG] |
| record each stage success/failure | worker | `IngestionStatus` timeline (per-stage status, attempt) | `unit/test_ingestion_service.py::test_every_stage_records_start_finish_status` [U]; `integration/test_content_api.py::test_get_version_returns_stage_runs` [PG,MN] |
| retry/resume | C5 + Celery retry | `IngestionStatus` "Retry" button | `unit/test_ingestion_service.py::test_resume_skips_succeeded_stages`, `::test_rerun_is_idempotent_no_duplicate_chunks` [U]; `test_content_api.py::test_retry_failed_ingestion_resumes_from_failed_stage` [PG,MN] |
| fail clearly on empty extraction | worker | red "Failed at EXTRACT/OCR: Text could not be extracted from this content. Upload a clearer file or enter a reference." (Section 37 text) | `unit/test_ingestion_service.py::test_empty_extraction_fails_asset_no_chunks_created`; `test_ingestion_e2e.py::test_ac004_negative_unreadable_scan_fails_no_empty_chunks` [PG,MN] |
| retain page/unit association | worker CHUNK | `ChunkViewer` shows unit + locator columns | `unit/test_chunking.py::test_page_association_retained`; `unit/test_unit_boundaries.py::*` (6) [U] |
| retrievable only under correct subject/version/approval scope | no endpoint (service `content_retrieval`, used by later phases) | **No UI** (internal service; Tutor is Phase 8) | `test_content_retrieval_scope.py::test_draft_version_chunks_excluded_from_approved_scope`, `::test_other_subject_chunks_never_returned`, `::test_superseded_chunks_not_in_active_scope_but_resolvable_by_id`, `::test_embedding_config_mismatch_not_compared` (+3) [PG] |
| partial failure not exposed as approved | worker | Version stays DRAFT, badge "Ingestion failed"; activate button disabled | `test_content_service.py::test_activate_rejected_when_ingestion_not_succeeded` [PG,MN] |

### FR-CON-003 Chunk Metadata and Traceability

| Verb | API | UI | Test |
|---|---|---|---|
| store metadata (`subject_id`, `content_version_id`, `unit_no`, `source_file`, locator, `chunk_type`) | worker STORE | `ChunkViewer` columns | `test_chunk_store.py::test_every_chunk_has_all_metadata_fields` [PG] |
| persist immutable reference | C7 | `ChunkViewer` "Resolve citation" drawer | `test_chunk_store.py::test_chunk_rows_are_insert_only`; `test_content_api.py::test_chunk_ref_resolves_to_version_file_locator_after_supersede` [PG,MN] |
| validate mandatory locator not null | DB CHECK + chunker | none | `test_chunk_store.py::test_null_or_empty_locator_rejected_by_check`; `unit/test_locators.py::*` [U] |
| external links create no chunks | C10 | none | `test_resource_link_service.py::test_link_never_creates_chunk_rows` [PG] |
| AI output traceable to version/file/locator | consumed in 2B (G4 topic source refs) | 2B Topic row "sources" | `test_curriculum_service.py::test_sampled_topic_traces_to_version_file_locator` [PG] (2B) |

### FR-CON-004 Immutable Versioning, Activation, and Rollback

| Verb | API | UI | Test |
|---|---|---|---|
| create immutable DRAFT version | C2 | "DRAFT" badge | `test_content_service.py::test_upload_creates_draft_version_with_sha_size_mime`; `integration/test_minio_store.py::test_write_once_key_second_put_rejected` [MN] |
| create DRAFT link | C10 / C13 | `ResourceLinks` "Revise" | `test_resource_link_service.py::test_revision_creates_new_draft_linked_to_prior_approved_untouched` [PG] |
| activate (Owner only) | C8 | `OwnerActions` "Activate" (visible to Owner only) | `test_content_service.py::test_owner_activates_v2_v1_superseded_but_traceable` (AC-005 positive); `::test_co_teacher_activation_rejected_403`; `::test_unassigned_teacher_activation_rejected_404` (AC-005 negative) [PG,MN]; `test_content_api.py::test_activate_endpoint_role_matrix` [PG,MN] |
| approve link (Owner only) | C12 | `ResourceLinks` "Approve" (Owner) | `test_resource_link_service.py::test_owner_approves_link`; `::test_co_cannot_approve_link` [PG] |
| roll back (Owner only) | C9 | `OwnerActions` "Rollback" | `test_content_service.py::test_owner_rolls_back_to_prior_valid_version_pointer_only`; `::test_rollback_to_failed_ingestion_version_rejected`; `::test_co_rollback_rejected` [PG,MN] |
| preserve dependent history / citations | C7 | superseded rows still listed | `test_content_service.py::test_prior_citations_remain_resolvable_after_activation_and_rollback` [PG,MN] |
| never edit approved content in place | no PUT/PATCH/DELETE routes | no edit control on active rows | `test_content_api.py::test_no_mutating_routes_for_versions_chunks_approved_links_405_404` [PG] |
| owner authorization | C8/C9/C12 | buttons absent for non-Owner; server rejects regardless | `test_content_service.py::test_activation_authorization_matrix_owner_co_primary_nonowner_unassigned` [PG,MN] |
| atomic activation | C8 | none | `test_content_service.py::test_concurrent_activation_leaves_exactly_one_active` (two real sessions) [PG] |
| audit | C8/C9/C12 + C2 | none (audit not UI in Phase 2) | `test_content_service.py::test_activate_rollback_upload_each_write_audit_row_same_txn` [PG,MN] |

Frontend tests (Vitest): `TeacherSubjects.test.tsx` (lists only assigned, shows Owner badge), `ContentUploadForm.test.tsx` (blocks >25 MB and bad ext client-side, shows server error), `IngestionStatus.test.tsx` (renders failed stage + Retry, Section 37 message), `OwnerActions.test.tsx` (hidden for CO, shown for Owner, 403 toast), `ResourceLinks.test.tsx`, `ChunkViewer.test.tsx`.

## 2A: Test counts (planned)

| Group | Files | Tests (approx) | Services |
|---|---|---|---|
| Unit: validation, MIME, parsers (4), cleaning, chunking, unit boundaries, locators, OCR adapter (fake), ingestion orchestrator (fake ports), embedding config, object-store key builder | 13 | 104 | none |
| PG: migration, content_service, resource_link_service, chunk_store, content_retrieval_scope | 5 | 42 | Postgres+pgvector |
| PG+MinIO: minio_store (9), content_api (28), ingestion_e2e (6) | 3 | 43 | Postgres+pgvector+MinIO |
| TS: ocr_tesseract | 1 | 2 | Tesseract binary |
| HF: embedding_hf (tokenizer/embedding) | 1 | 3 | HF model cache |
| Vitest | 6 | 16 | none |
| **Total 2A** | **29** | **~210** | |

Source files: 33 backend source + 6 infra + 10 frontend = **~49 new**, 12 changed.

---

# SLICE 2B — CURRICULUM (FR-CUR-001, FR-CUR-002, FR-CUR-003, FR-CUR-004)

Requires slice 2A: ACTIVE syllabus ContentVersion with ingestion SUCCEEDED, `content_chunks`, `embedding_configs`, embedder.

## 2A: As-built record (deviations from this plan, recorded 2026-10-04)

This section records where the implemented slice 2A differs from the plan above. The plan text above is kept as approved.

**Files added that the plan did not list**
- `backend/app/services/ingestion_repository.py`: SQL implementation of the IngestionService repository port (keeps the service free of database code).
- `backend/app/services/ingestion_runtime.py`: builds the ingestion context and wires adapters for the Celery task and tests.
- `backend/app/services/ingestion_retry.py`: pure retry rule for stuck jobs (finding M2).
- `backend/app/services/embedding_config_service.py`: get-or-create the active embedding configuration row.
- `backend/app/core/body_limit.py`: request-size middleware (findings M4, N1).
- Test helpers `backend/tests/support/` (`fakes.py`, `docs.py`, `world.py`, `content_helpers.py`).
- Unit tests beyond the plan's list: `test_upload_validation.py`, `test_mime_detection.py`, `test_parsers.py`, `test_object_store_keys.py`, `test_chunk_immutability.py`, `test_archive_limits.py`, `test_body_limit.py`, `test_ingestion_retry.py`, `test_unit_choice_and_worker_limits.py`, `test_denied_access_logging.py`; integration `test_verification_fixes.py`.

**Planned files not created**
- `unit/test_ocr_adapter.py`: the OCR behaviour it named (page without text triggers OCR, OCR failure names the page) is covered in `tests/unit/test_ingestion_service.py` with a fake OCR engine, and against real Tesseract in `tests/integration/test_ocr_tesseract.py`.
- The six planned Vitest files (`ChunkViewer`, `ContentUploadForm`, `IngestionStatus`, `OwnerActions`, `ResourceLinks`, `TeacherSubjects`) are consolidated into `TeacherContent.test.tsx`, plus `TeacherIngestionFixes.test.tsx` and `TeacherLinksFixes.test.tsx`.

**Naming**
- Enum CHECK constraints are named after the enum (for example `link_status`, `chunk_type`), following the Phase 1 convention, not `ck_<table>_<column>` as written above. Hand-written CHECKs use `ck_<table>_<rule>`.

**Behaviour decided after verification (see Approval for the human decisions)**
- Unit choice (P-6, finding m2): non-syllabus uploads choose one Unit or "All units"; a syllabus never takes a single Unit (N4); "All units" with no matching headings fails at CHUNK.
- Chunks: at most 800 tokens including the tokenizer's special tokens (798 content tokens); `content_chunks.embedding` is filled after insert by EMBED; a database trigger allows only that one change and blocks any update or delete once the version is approved (m6).
- Stuck jobs (M2): a RUNNING version can be retried after 40 minutes without activity (`content_versions.ingestion_heartbeat_at`).
- Limits (M5): Celery 25/30 minutes, 500 PDF pages, PPTX/DOCX 200 MB unpacked, ratio 100:1, 2,000 members.
- MinIO (M3, N6): no root fallback; a separate test user limited to the test bucket; storage misconfiguration returns a generic 503.
- Migration 0002 was edited in place after the first verification (never applied anywhere; any local database built from the earlier version must be recreated).

## 2B: Data model (SRS 31.2/31.3: CurriculumVersion/TopicVersion/TopicPrereq, AIProviderConfiguration/AgentRun)

| Table | Key columns / constraints |
|---|---|
| `similarity_thresholds` | `id`, `embedding_config_id` FK, `name` ('topic_duplicate'), `value` numeric(4,3) CHECK 0..1, `status` (`DRAFT|VALIDATED|ACTIVE`), `validation_report` JSON, `validated_by`, `validated_at`. Unique active per `(name)`. Initial row value 0.92, status DRAFT until validated (BUS-050). |
| `ai_provider_configurations` | `id`, `provider` (`ANTHROPIC|OPENAI`), `model` ('claude-opus-5-5'), `effort`, `max_output_tokens`, `token_budget`, `config_version`, `is_active`, `created_at`. One active per agent via partial unique index. No secrets. |
| `prompt_versions` | ADR-0017: `id`, `agent`, `version`, `content_sha256`, `body`, `output_schema`, `created_at`; unique `(agent, version)`; **append-only** (no UPDATE/DELETE path, DB rule or test). |
| `agent_runs` | `id`, `agent`, `provider_config_id` FK, `prompt_version_id` FK (ADR-0017), `subject_id`, `requested_by`, `curriculum_version_id` nullable, `input_refs` JSON (content_version_id, chunk ids; no Student data), `output` JSON, `status` (`RUNNING|SUCCEEDED|FAILED|REFUSED|QUEUED_RETRY`), token usage, attempts, `error`, timestamps. |
| `curriculum_versions` | `id`, `subject_id`, `version_no` (unique per subject), `status` (`GENERATING|GENERATION_FAILED|DRAFT|ACTIVE|SUPERSEDED|RETURNED`), `origin` (`AGENT|FLAT_FALLBACK`), `source_content_version_id` FK, `agent_run_id` FK nullable, `embedding_config_id`, `similarity_threshold_id`, `revision` int (bumped per edit), `validated_revision` int nullable, `validation_status` (`NOT_RUN|PASSED|BLOCKED`), `created_by`, `decided_by`, `decided_at`, `decision_reason`, `supersedes_version_id`, `activated_at`. **Partial unique index** `uq_one_active_curriculum_per_subject (subject_id) WHERE status='ACTIVE'`. |
| `topics` | `id` (stable topic key), `subject_id`, `created_at`. |
| `topic_versions` | `id`, `topic_id` FK, `curriculum_version_id` FK, `unit_id` FK nullable (orphan if null), `name`, `outcomes` JSON (>=1), `bloom_level` (`REMEMBER..CREATE`), `est_hours` numeric CHECK >0, `classification` (`CORE|OPTIONAL|SELF_STUDY`), `order_index`, `embedding vector(1024)` nullable, `embedding_config_id`; unique `(curriculum_version_id, topic_id)`. Exam weightage is **not stored**: derived from `units.weightage` (Section 18 "inherit"). |
| `topic_prereqs` | `id`, `curriculum_version_id`, `topic_id`, `prereq_topic_id`, `prereq_curriculum_version_id` nullable (pins cross-subject edge to the earlier Subject's exact version), `confidence` numeric CHECK 0..1, `approved_by_teacher` bool, `source` (`AGENT|TEACHER`), `dropped` bool, `drop_reason`; unique `(curriculum_version_id, topic_id, prereq_topic_id)`; CHECK `topic_id <> prereq_topic_id`. |
| `topic_mappings` | `id`, `curriculum_version_id`, `kind` (`RENAME|MERGE|SPLIT`), `from_topic_id`, `to_topic_id`, `created_by` (merge/split lineage retained, Section 18). |
| `graph_validation_flags` | `id`, `curriculum_version_id`, `revision`, `kind` (`CYCLE_EDGE_DROPPED|ORPHAN|DUPLICATE_TOPIC|SCOPE_VIOLATION`), `topic_id`, `other_topic_id`, `edge_id`, `detail` JSON (cycle path, confidence, similarity, threshold id, embedding config id), `blocking` bool, `resolved` bool. |
| `topic_source_chunks` | `topic_version_id`, `content_chunk_id` (FR-CON-003 immutable refs). |

All `pg_only`.

## 2B: Migration plan

`backend/alembic/versions/0003_curriculum_schema.py`, `down_revision = "0002"`: creates the tables above with named CHECKs (ADR-0009), partial unique indexes (`uq_one_active_curriculum_per_subject`, one active provider config per agent), HNSW not needed on `topic_versions.embedding` (small set; sequential scan). Round-trip upgrade/downgrade tested on PostgreSQL. Seed rows (initial 0.92 threshold, default provider config, prompt sync) are inserted by the startup sync and `seed_curriculum_config.py`, not the migration.

## 2B: Files to create

Backend source (30):
| Path | Purpose |
|---|---|
| `backend/alembic/versions/0003_curriculum_schema.py` | Migration |
| `backend/app/models/curriculum.py` | `CurriculumVersion`, `Topic`, `TopicVersion`, `TopicPrereq`, `TopicMapping`, `GraphValidationFlag`, `TopicSourceChunk`, `SimilarityThreshold` |
| `backend/app/models/ai.py` | `AIProviderConfiguration`, `PromptVersion`, `AgentRun` |
| `backend/app/schemas/curriculum.py` | Generate/response/graph/edit/decision schemas |
| `backend/app/schemas/curriculum_agent.py` | Strict Pydantic LLM output schema (Units/Topics/outcomes/Bloom/hours/edges + confidence, source chunk refs) |
| `backend/app/api/routes/teacher_curriculum.py` | Endpoints G1..G15 |
| `backend/app/services/curriculum_graph.py` | **Pure deterministic**: DFS cycle detect/break with tie-break, orphan, duplicate (cosine > threshold), flat-order builder; no DB, no LLM |
| `backend/app/services/curriculum_service.py` | Generation request, persist DRAFT, run validation, approve/reject/fallback (row lock + atomic pointer), audit |
| `backend/app/services/curriculum_edit_service.py` | rename/merge/split/reorder/classify/hours/edges/delete topic; revision bump; revalidate; lineage |
| `backend/app/services/similarity_config_service.py` | Resolve active versioned threshold + embedding config; activation guard (validated) |
| `backend/app/integrations/llm/__init__.py`, `base.py` | Provider-neutral `LLMProvider` Protocol + `StructuredResult` |
| `backend/app/integrations/llm/anthropic_adapter.py` | `langchain-anthropic` adapter for `claude-opus-5-5` (handles ADR-0016 behaviours) |
| `backend/app/agents/__init__.py`, `curriculum_agent.py` | Generate -> schema validate -> retry-with-repair (bounded) -> return validated object + run record; coordinates only (P-14) |
| `backend/app/prompts/__init__.py`, `registry.py` | TOML loader, SHA-256 sync into `prompt_versions`, fail-startup on hash mismatch (ADR-0017) |
| `backend/app/prompts/curriculum/v1.toml` | First prompt (system/user templates, schema name, notes) |
| `backend/app/workers/curriculum_tasks.py` | `generate_curriculum(version_id)` idempotent, retry on outage |
| `backend/scripts/validate_similarity_threshold.py` | Runs labelled pair set with the real embedder; writes `validation_report`, sets threshold VALIDATED/DRAFT (P-7) |
| `backend/scripts/seed_curriculum_config.py` | Provider config + initial threshold rows |
| `backend/scripts/seed_phase2_curriculum_demo.py` | Demo: cyclic stub output, CO edit, Owner activation |
| `backend/tests/fixtures/curriculum/*.json` (3-4) | Stub LLM outputs: valid, cyclic (0.8/0.4), tie, schema-broken, refusal |
| `backend/tests/fixtures/duplicate_pairs.json` | Labelled duplicate/non-duplicate topic-name pairs (P-7) |

Frontend (2B), 9: `types/curriculum.ts`, `api/curriculumApi.ts`, `pages/teacher/CurriculumPage.tsx`, `CurriculumVersionList.tsx`, `TopicEditor.tsx`, `EdgeEditor.tsx`, `ValidationPanel.tsx`, `OwnerDecisionBar.tsx`, `MergeSplitDialogs.tsx`.

## 2B: Files to change

| Path | Change |
|---|---|
| `backend/app/models/__init__.py` | Import `curriculum`, `ai` |
| `backend/app/main.py` | Register `teacher_curriculum`; call prompt registry sync at startup (lifespan) |
| `backend/app/core/config.py` | `llm_provider`, `llm_model`, `llm_effort`, `llm_token_budget`, `anthropic_api_key` (env only), repair-attempt limit, duplicate threshold default |
| `backend/app/workers/celery_app.py` | Register curriculum tasks; sync prompts at worker start |
| `backend/pyproject.toml` | Add `langchain-anthropic`, `langchain-core` (+ `langgraph` only if P-14 says so); marker `llm_live` |
| `.env.example` | `LLM_PROVIDER`, `LLM_MODEL`, `LLM_EFFORT`, `LLM_TOKEN_BUDGET`, `ANTHROPIC_API_KEY=` (blank) |
| `frontend/src/components/TeacherShell.tsx` | Add Curriculum tab |
| `backend/tests/conftest.py` | `stub_llm` fixture, fake embedder fixture (done in 2A) |

## 2B: API endpoints

Router `teacher_curriculum.py`, prefix `/teacher`, role TEACHER, CSRF on mutations.

| # | Method + Path | Guard | Purpose |
|---|---|---|---|
| G1 | `POST /teacher/subjects/{subject_id}/curriculum/generate` -> 202 | Assigned; rate-limited; 409 if no ACTIVE syllabus version | Create `GENERATING` version + enqueue `generate_curriculum` |
| G2 | `GET /teacher/subjects/{subject_id}/curriculum/versions` | Assigned | Version chain with statuses |
| G3 | `GET /teacher/subjects/{subject_id}/curriculum/active` | Assigned | Current ACTIVE graph (what Question generation/planning will use) |
| G4 | `GET /teacher/curriculum/versions/{cid}` | Assigned | Full graph: Units, Topics, outcomes, edges, flags, validation, agent run status, source chunk refs |
| G5 | `POST /teacher/curriculum/versions/{cid}/validate` | Assigned (DRAFT only) | Re-run deterministic validation |
| G6 | `PATCH /teacher/curriculum/versions/{cid}/topics/{topic_id}` | Assigned (DRAFT only) | Rename, classify, est_hours, outcomes, Bloom, assign Unit |
| G7 | `POST /teacher/curriculum/versions/{cid}/topics/merge` | Assigned | Merge topics; mapping retained |
| G8 | `POST /teacher/curriculum/versions/{cid}/topics/{topic_id}/split` | Assigned | Split into parts; mapping retained |
| G9 | `PUT /teacher/curriculum/versions/{cid}/units/{unit_id}/topic-order` | Assigned | Reorder topics within a Unit |
| G10 | `POST /teacher/curriculum/versions/{cid}/edges` | Assigned | Add prerequisite edge |
| G11 | `DELETE /teacher/curriculum/versions/{cid}/edges/{edge_id}` | Assigned | Delete edge |
| G12 | `DELETE /teacher/curriculum/versions/{cid}/topics/{topic_id}` | Assigned | Remove topic (orphan resolution per Section 18) |
| G13 | `POST /teacher/curriculum/versions/{cid}/approve` `{reason}` | **Owner** | Validated DRAFT -> ACTIVE, prior -> SUPERSEDED, atomic, audit |
| G14 | `POST /teacher/curriculum/versions/{cid}/reject` `{reason}` | **Owner** | DRAFT -> RETURNED; prior ACTIVE unchanged; audit |
| G15 | `POST /teacher/subjects/{subject_id}/curriculum/fallback` `{reason}` | **Owner**; only when no ACTIVE exists | Create+activate flat Unit-order version, no edges; audit |

Non-HTTP: Celery `generate_curriculum`; CLI `validate_similarity_threshold.py` (threshold validation has no UI in Phase 2; the Teacher UI shows the threshold/model version and a "threshold not validated" blocker).

## 2B: Verb -> endpoint / UI / test traceability

### FR-CUR-001 Curriculum Version Extraction

| Verb | API | UI | Named test(s) |
|---|---|---|---|
| request generation | G1 | `CurriculumPage` "Generate curriculum" button (assigned Teachers) | `integration/test_curriculum_api.py::test_assigned_teacher_generate_returns_202_generating` [PG]; `::test_generate_without_active_syllabus_409` ; `::test_unassigned_teacher_generate_404` |
| extract Topics/outcomes/Bloom/hours/edges (Curriculum Agent) | worker `generate_curriculum` | version row shows "GENERATING" then "DRAFT"; on outage "Queued, will retry" | `unit/test_curriculum_agent.py::test_valid_output_accepted`; `::test_llm_outage_queues_retry_status_not_partial_draft` [U]; `integration/test_curriculum_service.py::test_generation_persists_topics_edges_outcomes_with_stable_ids` [PG] |
| strict schema + retry-with-repair | agent | none (failure shown as status) | `test_curriculum_agent.py::test_schema_violation_triggers_repair_then_succeeds`; `::test_repair_exhausted_fails_safely_no_topics_created` [U] |
| validate required fields / ranges | agent + service | status `GENERATION_FAILED` + message | `::test_confidence_out_of_range_rejected`, `::test_invalid_bloom_rejected`, `::test_est_hours_nonpositive_rejected`, `::test_topic_with_two_units_or_none_rejected` [U] |
| earlier-semester cross-subject scope | service | edge shows source Subject chip | `test_curriculum_service.py::test_cross_subject_edge_to_same_or_later_semester_rejected`; `::test_cross_subject_edge_to_earlier_semester_pinned_to_exact_version` [PG] |
| inherit Unit exam weightage | service | Topic row shows weight (read-only, from Unit) | `test_curriculum_service.py::test_topic_weightage_derived_from_unit_not_stored` [PG] |
| content-version references (source chunks) | service | Topic "sources" popover -> chunk viewer | `::test_sampled_topic_traces_to_version_file_locator` [PG] |
| current ACTIVE remains available | G3 | "Active" badge unchanged while DRAFT exists | `::test_active_version_unchanged_while_draft_generated` [PG] |
| create DRAFT / fail safely | agent + service | `GENERATION_FAILED` badge with reason | `::test_refusal_stop_reason_marks_run_refused_no_graph` [U] |
| log run (versioned prompt, provider/model/config, tokens) | agent | none (not UI in Phase 2) | `integration/test_agent_runs_logging.py::test_run_records_prompt_version_fk_provider_config_tokens_and_input_refs` [PG] |
| Anthropic API behaviours (no forced tool_choice, effort set, no temperature, refusal) | adapter | none | `unit/test_llm_provider_contract.py::test_anthropic_request_has_no_temperature_top_p_top_k_or_forced_tool_choice`, `::test_effort_set_explicitly`, `::test_refusal_maps_to_refused` [U] |
| prompt registry sync | startup | none | `unit/test_prompt_registry.py::*` (8) + `integration`: `::test_hash_mismatch_fails_startup`, `::test_agent_run_fk_resolves_prompt_text` [PG] |

### FR-CUR-002 Graph Validation

| Verb | API | UI | Test |
|---|---|---|---|
| DFS cycle detection | auto after generation/edit; G5 | `ValidationPanel` lists cycles | `unit/test_curriculum_graph.py::test_two_node_cycle_detected` |
| drop + flag lowest-confidence edge | same | flagged edge shown struck-through with reason, banner "A prerequisite cycle was detected. Review the flagged relationship." | `::test_ac006_drops_0_4_edge_keeps_0_8_acyclic` [U] |
| tie-break ascending normalized `(topic_id, prereq_topic_id)`, drop first | same | same | `::test_equal_confidence_drops_ascending_first`, `::test_normalization_is_case_insensitive_uuid_compare` [U] |
| repeat until acyclic | same | same | `::test_overlapping_cycles_repeat_until_acyclic`, `::test_self_loop`, `::test_result_always_acyclic_property` [U] |
| flag orphans | same | orphan badge on Topic, "Assign Unit"/"Remove" | `::test_orphan_topic_flagged_blocking` [U]; `test_curriculum_service.py::test_orphan_blocks_approval` [PG] |
| flag duplicates (> threshold) | same | duplicate pair list with similarity | `::test_duplicate_flagged_only_strictly_above_0_92`, `::test_0_92_exact_not_flagged` [U]; `integration/test_topic_duplicate_pgvector.py::test_duplicates_from_stored_vectors_same_config_only` [PG] |
| versioned model/threshold reference | service | panel shows model id/revision + threshold + "validated?" | `test_curriculum_service.py::test_validation_records_embedding_config_and_threshold_ids` [PG] |
| changed model/threshold cannot activate before validation | G13 | Approve disabled with reason | `::test_unvalidated_threshold_blocks_activation`; `unit/test_similarity_threshold.py::*` (6) [U/PG]; `integration/test_duplicate_threshold_validation.py::test_labelled_set_meets_acceptance_criteria` [HF] |
| notify Teacher | G4 response + banner | `ValidationPanel` banner (persistent Notification entity is Phase 9, P-10) | `test_curriculum_api.py::test_dropped_edge_flag_visible_in_graph_response` [PG] |
| validated draft -> review | G4 | review enabled | `::test_validation_runs_before_review_and_graph_acyclic_unit_linked` [PG] |

### FR-CUR-003 Teacher Graph Editing

| Verb | API | UI | Test |
|---|---|---|---|
| rename | G6 | `TopicEditor` inline name input | `test_curriculum_edit.py::test_rename_keeps_stable_id_and_records_mapping` [PG] |
| merge | G7 | `MergeSplitDialogs` merge dialog | `::test_merge_maps_old_ids_to_target_and_remaps_edges` |
| split | G8 | split dialog | `::test_split_maps_to_parts_and_assigns_edges_explicitly` |
| reorder | G9 | up/down buttons per Unit (no drag library) | `::test_reorder_within_unit_persists_order_index` |
| classify (Core/Optional/Self-study) | G6 | classification select | `::test_classify_each_enum`, `::test_invalid_classification_400` |
| change estimated hours | G6 | hours number input | `::test_hours_must_be_positive` |
| add edge | G10 | `EdgeEditor` add-prereq form | `::test_add_edge_triggers_revalidation_and_new_cycle_blocks_approval` |
| delete edge | G11 | `EdgeEditor` delete | `::test_delete_edge_revalidates` |
| remove Topic / assign Unit (orphan) | G12 / G6 | `TopicEditor` remove / unit select | `::test_delete_topic_removes_incident_edges`, `::test_assign_unit_clears_orphan_flag` |
| save version + rerun validation | every edit | validation panel refreshes | `::test_every_edit_bumps_revision_and_reruns_validation` |
| preserve/map stable IDs | merge/split | n/a | covered above |
| approval remains pending after material change | G13 | Approve disabled until revalidated | `test_curriculum_service.py::test_approve_blocked_when_validated_revision_is_stale` |
| CO Teacher edits allowed; unassigned rejected | G6..G12 | edit controls visible to all assigned | `test_curriculum_edit.py::test_co_teacher_can_edit`, `::test_unassigned_teacher_edit_404`, `::test_edit_on_active_version_rejected_409` |
| no invalid graph approved | G13 | blocked message | `test_curriculum_service.py::test_remaining_cycle_blocks_approval_ac006_negative` |

### FR-CUR-004 Subject Owner Approval and Fallback

| Verb | API | UI | Test |
|---|---|---|---|
| approve / activate | G13 | `OwnerDecisionBar` "Approve and activate" with reason (Owner only) | `test_curriculum_service.py::test_ac007_owner_approves_valid_draft_becomes_active_prior_superseded_traceable` |
| reject | G14 | "Reject (return to draft)" with reason | `::test_reject_returns_draft_prior_active_unchanged` |
| select fallback (no prior ACTIVE) | G15 | "Activate flat Unit order" (only shown when no ACTIVE) | `::test_fallback_only_when_no_active_and_owner`, `::test_fallback_has_no_edges_and_unit_order`, `::test_fallback_rejected_when_active_exists` |
| CO approval blocked | G13/G14/G15 | controls hidden for non-Owner | `::test_co_teacher_approval_blocked_403` (AC-007 negative) |
| audit decision | G13/G14/G15 | n/a (no audit UI) | `::test_decisions_write_audit_rows_same_txn` |
| atomic active-pointer update | G13 | n/a | `::test_failure_mid_transition_leaves_prior_active`, `::test_concurrent_approvals_single_active` (two real sessions) |
| Owner authorization | G13-15 | as above | `test_curriculum_api.py::test_owner_only_endpoints_role_matrix` |
| Question generation/planning use ACTIVE | G3 | Active graph view | `::test_get_active_returns_active_chain_and_prior_resolvable` |
| no invalid AI graph activates | G13 | blocked message | `::test_agent_failed_version_cannot_be_approved` |

### Section 43 demo (end-to-end, both slices)

`integration/test_phase2_demo_flow.py` [PG,MN] with stub LLM: (1) Owner uploads+activates a syllabus; (2) Teacher requests generation, stub returns the cyclic graph (A->B 0.8, B->A 0.4); (3) 0.4 edge dropped/flagged; (4) CO Teacher edits (rename/classify) and attempts approve => 403; (5) Owner approves the corrected graph => ACTIVE; (6) prior ACTIVE chain still resolvable via G2/G4/C7. Plus `::test_demo_second_activation_supersedes_prior_chain_resolvable`. A `llm_live` marker test (skipped without `ANTHROPIC_API_KEY`) runs one real generation.

## 2B: Test counts (planned)

| Group | Files | Tests (approx) | Services |
|---|---|---|---|
| Unit: curriculum_graph (24), flat fallback (4), llm contract (10), curriculum_agent (12), prompt_registry (8), similarity_threshold (6), no-LLM-in-deterministic static import test (3) | 7 | 67 | none |
| PG: migration (4), curriculum_service (30), curriculum_edit (22), curriculum_api (30), agent_runs_logging (6), topic_duplicate_pgvector (5), demo flow (3) | 7 | 100 | Postgres+pgvector (+MinIO for demo flow) |
| HF: duplicate-threshold validation | 1 | 2 | HF model cache |
| LIVE: curriculum live smoke | 1 | 1 | Anthropic API key (optional) |
| Vitest | 6 | 18 | none |
| **Total 2B** | **22** | **~188** | |

Source files: 30 backend + 9 frontend = **~39 new**, 8 changed.

---

# Test Infrastructure change (applies to both slices)

## Current state (verified)

- `backend/tests/conftest.py`: in-memory SQLite (`create_engine("sqlite://", StaticPool)`, `Base.metadata.create_all`), `FakeRedis`, `TestClient` with `get_db` overridden.
- `backend/pyproject.toml`: `testpaths = ["tests"]`, `addopts = "--cov=app.services --cov-report=term-missing"`; no markers.
- No CI, no Dockerfile, Docker unavailable in the planning environment.

## What changes

1. **Markers** (registered, `--strict-markers`): `pg`, `minio`, `tesseract`, `hf_model`, `llm_live`. A test touching pgvector/Postgres features is `@pytest.mark.pg`; anything asserting bytes in MinIO is `@pytest.mark.minio`.
2. **No SQLite for Phase 2.** Phase 2 tables set `Table.info={"pg_only": True}`. The existing `engine` fixture changes to `Base.metadata.create_all(eng, tables=[t for t in Base.metadata.sorted_tables if not t.info.get("pg_only")])`, so all Phase 1 tests keep running unchanged on SQLite. Every Phase 2 test that needs a database uses the new Postgres fixtures; pure-unit tests use none.
3. **Postgres fixtures** (use the compose `postgres` service from `docker-compose.yml`, image `pgvector/pgvector:pg15`):
   - `pg_admin_url` from `TEST_DATABASE_URL` (default `postgresql+psycopg://uniadapt:uniadapt@localhost:5432/uniadapt_test`), derived admin URL for `CREATE DATABASE`.
   - session-scoped `pg_engine`: drops/creates `uniadapt_test`, runs **`alembic upgrade head`** (so migrations `0002`/`0003` are exercised every run; never `create_all`), asserts `vector` extension present.
   - function-scoped `pg_session`: connection + outer transaction + `Session(join_transaction_mode="create_savepoint")`, rolled back after each test (service-layer `commit()` is safe).
   - function-scoped `pg_committed` (+ TRUNCATE ... CASCADE teardown) for tests that need real commits across sessions: concurrent-activation tests and Celery-task tests.
   - `pg_client`: `TestClient` with `get_db` bound to `pg_session`, `get_object_store` bound to the real MinIO store, `get_ingestion_queue` bound to a recorder or to eager execution; cookie-secure handling copied from the existing `client` fixture.
4. **MinIO fixtures** (compose `minio` service): session-scoped `minio_store` from `TEST_MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY` (default `localhost:9000`); creates test bucket `uniadapt-content-test` (bucket name is config, so dev data in `uniadapt-content` is never touched) and applies the same private policy and scoped credential flow as `bootstrap_minio.sh`; per-test unique `subject_id` prefix, objects removed at teardown. The `FakeObjectStore` exists **only** for `IngestionService` orchestration unit tests through the `ObjectStore` Protocol; any test asserting key layout, write-once, privacy, scoped-credential, sha256 integrity, or "bytes are in MinIO" uses the real service.
5. **Failure policy, not silent skipping.** If a `pg`/`minio` test runs and the service is unreachable, the fixture **fails** with an instruction to run `docker compose up -d --wait postgres minio`. Skipping is only allowed when `UNIADAPT_TEST_ALLOW_SKIP=1` is set explicitly (for developer machines without Docker); CI never sets it. This prevents a green run that silently tested nothing.
6. **Pure unit tests (no services, always runnable):** validators, MIME detection, parsers (fixtures generated in-memory), cleaning, chunking (with a deterministic whitespace `FakeTokenizer`), unit boundaries, locators, OCR adapter logic (with `FakeOcrEngine`), `IngestionService` with fake ports, object-store key builder, curriculum_graph, LLM adapter request building and contract tests (stubs), curriculum_agent (stub provider), prompt-registry file/hash logic, similarity-threshold logic with synthetic vectors, static import-boundary test, Vitest.
7. **Heavy/optional external tests:** `tesseract` (needs the binary; runs inside the backend Docker image/CI image), `hf_model` (real bge-m3 tokenizer/model; large download, uses `HF_HOME` cache volume; excluded from default CI with `-m "not hf_model"`, run before verification), `llm_live` (needs `ANTHROPIC_API_KEY`, skipped otherwise).
8. **How runs bring up services**
   - Local: `backend/scripts/test_services.sh` = `docker compose up -d --wait postgres minio minio-init` -> `pytest` (all markers except `hf_model`/`llm_live` by default) -> optional `docker compose down`. Pure-unit only: `pytest -m "not pg and not minio and not tesseract and not hf_model and not llm_live"`.
   - CI (`.github/workflows/backend-tests.yml`): checkout, `docker compose up -d --wait postgres minio minio-init`, run tests inside the backend image (so Tesseract is present), env `TEST_DATABASE_URL`/`TEST_MINIO_*` set; `hf_model` job optional/nightly with HF cache. The workflow file is committed locally only; publishing is out of this agent's scope.
9. **Coverage:** keep `--cov=app.services`; add `--cov=app.integrations` is NOT required. Add a gate step (script/CI) `coverage report --include="app/services/ingestion_service.py,app/services/ingestion/*,app/services/curriculum_graph.py" --fail-under=80` (NFR-TST-001). Boundary/failure cases are explicit in the test names above.

---

# Exact-Algorithm Call-Outs

- **Sections 23, 24, 25 (Mastery Score, Engagement Score, Adaptive Study Planner): not touched by Phase 2.** No formula is implemented or approximated.
- **Phase-2 deterministic algorithms that must be implemented exactly as specified (FR-CUR-002 / Section 18, not approximated):**
  - Cycle handling: DFS; for each detected cycle drop the single lowest-confidence edge; ties broken by sorting normalized `(topic_id, prereq_topic_id)` ascending and dropping the first; flag it; repeat until acyclic.
  - Duplicate detection: cosine similarity on normalized vectors, flagged when strictly `> threshold` (initial `0.92`), only between vectors with the same `embedding_config_id`.
  - Chunking: <=800 embedding-model tokens (bge-m3 tokenizer, same pinned revision), 120-token overlap, no crossing of a known Unit boundary, final chunk may be shorter.
- **AI/deterministic boundary:** `IngestionService`, `ingestion/**`, `curriculum_graph.py`, and the DB-level approve/fallback gates never call an LLM or import `app.agents`/`app.prompts`/`langchain*`/`anthropic`. The Curriculum Agent output is only an input to deterministic validation; no LLM re-scores, re-orders, or "repairs" a validation result. Retry-with-repair applies only to schema-invalid LLM output before it enters validation.

---

# Decisions Applied

| ADR | How the plan follows it |
|---|---|
| ADR-0001 (cookie JWT + CSRF) | All new mutating routes include `csrf_protect`; frontend uses the existing `apiRequest` (multipart sets no manual Content-Type). |
| ADR-0002 (Unit weight service layer) | Phase 2 only reads Units; the flat fallback and `unit_no` use existing Units; no direct writes to `units`. Teacher editing of Unit exam weightage is not added (Admin-only through `subject_service`). |
| ADR-0003 (single Subject Owner) | Owner = `SubjectOwnerAssignment.owner_teacher_id`; activation/rollback/approval guards read it; no history table (audit_logs only). |
| ADR-0006 (Redis rate limit) | Upload and generate endpoints use the existing `RateLimiter`, limits from config. |
| ADR-0009 (VARCHAR+CHECK) | Every Phase 2 enum is `native_enum=False, create_constraint=True` with `ck_<table>_<col>` names. |
| ADR-0010 (supporting libs) | No Vite/dotenv/PyJWT alternatives introduced. |
| ADR-0011 (audit every mutation) | Every create/update/delete/decision in both slices calls `audit.record` in the same transaction with explicit `actor`. |
| ADR-0013 (Tesseract) | `pytesseract`, `eng` only, per-page OCR, pinned config/version stored in `ingestion_stage_runs.detail`; `tesseract-ocr` + `tesseract-ocr-eng` installed in `backend/Dockerfile`. Thresholds are config values pending P-4. |
| ADR-0014 (parsers) | pdfplumber + pypdfium2 render at fixed DPI, python-pptx, python-docx, stdlib strict UTF-8; locators `page:`/`slide:`/`section:...#p<i>`/`lines:a-b`; images in PPTX/DOCX skipped. PPTX notes and Unit-boundary detection pending P-5/P-6. |
| ADR-0015 (bge-m3) | `vector(1024)`, normalized cosine, local CPU sentence-transformers, tokenizer from the same pinned revision for chunking, `embedding_configs` row referenced by every chunk and topic embedding, same-config comparison only, `0.92` stored as a versioned `similarity_thresholds` row that must be VALIDATED before activation (P-7, P-9). |
| ADR-0016 (Anthropic first) | Provider-neutral interface; `langchain-anthropic` adapter; default `claude-opus-5-5` from config; no forced `tool_choice`; effort set explicitly and stored in `ai_provider_configurations`; no `temperature/top_p/top_k`; `refusal` stop reason => failed run; ASM-004 outage => queued retry and Owner can still use flat fallback. OpenAI adapter timing is P-3. Structured-output mode is confirmed by spike S-1. |
| ADR-0017 (prompt registry) | `backend/app/prompts/curriculum/v1.toml`, `tomllib`, SHA-256 sync into append-only `prompt_versions`, hash mismatch fails startup, `agent_runs.prompt_version_id` FK; deterministic services never import `app/prompts` (static test). |
| ADR-0018 (MinIO layout) | Bucket `uniadapt-content` (config), key `subjects/{subject_id}/assets/{content_asset_id}/versions/{content_version_id}/original.{ext}` with `ext` from the validated type, write-once put, scoped service credential (never root), sha256/size/MIME on `content_versions`, no derived artifacts in MinIO, rollback is a pointer change only, `bootstrap_minio.sh` + config + `.env.example` entries. Client library is P-2. |
| ADR-0004/0005/0007/0008/0012 | Not applicable to Phase 2. |

---

# Implementation order and spikes

Spikes (done first in 2A/2B, recorded as plan deviations if they change anything):
- S-0 (2A): confirm the host/CI has Docker; if not, stop (R-1).
- S-1 (2B): with a stub and then a real key, confirm which structured-output mode `langchain-anthropic` uses for `claude-opus-5-5` and that it never sends forced `tool_choice`. If the helper forces a tool, fall back to the adapter calling the `anthropic` SDK's native JSON-schema output (a transitive dependency); document in the plan.
- S-2 (2A): resolve the pinned bge-m3 revision (P-9) and verify an 800-token chunk is not truncated.

Order: 2A (models/migration -> pure ingestion pieces -> ports/adapters -> orchestrator -> worker -> content/link services -> routes -> UI -> demo seed) -> 2A verification checkpoint (commit) -> 2B (models/migration -> pure graph -> prompt registry/provider/agent -> services -> routes -> UI -> demo) -> full demo test -> `update-claude-md`.

---

# Risks & Open Questions

Items needing a human decision are written as **proposed ADRs (P-n)**. Nothing below has been decided or accepted by this agent; where a recommendation is given, the plan's code reads configuration so either answer is a config/small change. Each is blocking for the listed step unless noted.

## Risks

- **R-1 Docker unavailable.** The planning environment has no `docker`. pgvector, MinIO, Tesseract, and Celery integration tests cannot run without it. Implementation can be written, but acceptance evidence requires a Docker host for the implementer/verifier. Ask: confirm the verifier machine has Docker Desktop/Engine.
- **R-2 No Dockerfiles in repo** (Phase 1 gap). 2A adds `backend/Dockerfile`. The frontend Dockerfile stays missing (out of scope); `docker compose up` for the full stack still will not build `frontend`.
- **R-3 Image size and cold start.** bge-m3 (~2.3 GB weights) plus CPU torch makes the backend/celery image and first ingestion slow. Mitigation: HF cache volume, model loaded once per worker, `hf_model` tests excluded from default CI.
- **R-4 ADR-0015 sign-off.** ADR-0015 states `sentence-transformers`/torch needs "explicit human sign-off as an addition beyond the fixed stack". It is Accepted, but please confirm the acceptance covers that sign-off (see P-8).
- **R-5 Real-LLM behaviour is unverified.** Quality of Opus-generated graphs and the exact structured-output mode are untested until a key is available (S-1, `llm_live`). Contract/stub tests cover the rest.
- **R-6 OCR quality** on photographed/handwritten pages is limited by ADR-0013 (English printed text only); failures surface as per-page errors by design.
- **R-7 Large PDFs.** 25 MB PDF with many scanned pages makes OCR slow; ingestion runs only in Celery; add a per-version timeout config. Streaming upload to a spooled temp file with a hard 25 MB cap (P-12).
- **R-8 Uncommitted ADR files** (see mismatch 4) and a likely `.gitignore` miss for `tsconfig.tsbuildinfo`.

## Proposed ADRs and decisions (need human approval)

- **P-1 Actual-MIME detection for NFR-SEC-009.** Options: (A, recommended) stdlib signature + structure checks per allowed type (PDF `%PDF-` header; PPTX/DOCX = valid ZIP containing `ppt/presentation.xml`/`word/document.xml`; TXT = strict UTF-8, no NULs) with no new dependency; (B) `filetype` or `puremagic` (pure Python); (C) `python-magic` (needs system `libmagic`). Affects `ingestion/mime.py` only.
- **P-2 MinIO Python client and admin bootstrap.** `minio` SDK (recommended; small, MinIO-native) vs `boto3` (heavy, S3-generic). Neither SDK creates scoped service accounts/policies; the bootstrap needs the `mc` CLI, so the plan adds a one-shot `minio-init` compose service using the `minio/mc` image. Confirm that image is acceptable "MinIO tooling" under Section 45 and not "new infrastructure".
- **P-3 OpenAI adapter timing (ADR-0016 left open).** Options: (A, recommended) build the provider-neutral interface and Anthropic adapter now, the OpenAI adapter as a named follow-up in Phase 3 (second LLM phase), with stub contract tests for the interface now; (B) build `langchain-openai` adapter in Phase 2, stub-tested only. NFR-AI-004's "contract tests against both adapters" is satisfied once both exist.
- **P-4 "No usable text" thresholds (ADR-0013 left open).** Proposed config defaults: a page "has usable text" if >= 25 non-whitespace characters after extraction; Tesseract 5 `--oem 1 --psm 3`, render DPI 300; an OCR page fails if mean word confidence < 60 or < 25 characters; a visually blank page (near-white image) is skipped, not failed; any non-blank failing page fails the version at that page (no partial approval). Needs approval of numbers and of "any page fails => version fails" vs a tolerated percentage.
- **P-5 PPTX speaker notes (ADR-0014 left open).** Recommend ingest notes as separate segments with locator `slide:<n>#notes` (they carry teaching content; same chunk_type); alternative: skip. Embedded images in PPTX/DOCX are skipped per ADR default.
- **P-6 Unit-boundary detection in multi-unit files (ADR-0014/FR-CON-002 left open).** Recommend: (1) per-upload Unit selected by the Teacher applies to the whole file (notes/PYQ/lab); (2) for a syllabus or "all units" upload, deterministic heading detection (`^\s*(unit|module)\s*[-:]?\s*(\d+|[ivx]+)\b`, case-insensitive) matched in order to the Subject's Units by `order_index`; text before the first heading gets `unit_no = NULL` and is flagged; syllabus ingestion fails if zero headings match. Open: allow `NULL unit_no` chunks for non-syllabus content with no Unit chosen?
- **P-7 Duplicate-threshold (`0.92`) validation set and acceptance bar (ADR-0015 requires the plan to define it).** Proposal: `backend/tests/fixtures/duplicate_pairs.json` with ~60 labelled Topic-name+outcome pairs from synthetic engineering syllabi (30 true duplicates/paraphrases, 30 related-but-distinct), run with the real bge-m3 via `validate_similarity_threshold.py`; record precision/recall and the confusion at 0.92 in `similarity_thresholds.validation_report`; the threshold becomes VALIDATED only if precision >= 0.90 and recall >= 0.80 (numbers need approval). If it fails, a different value is a new versioned threshold row, still human-approved. Phase 3/8 thresholds (`0.70`, `0.85`) are out of scope.
- **P-8 Supporting-library approval bundle** (extends ADR-0010 style): `pytesseract` (ADR-0013), `pdfplumber`, `pypdfium2`, `python-pptx`, `python-docx` (ADR-0014), `sentence-transformers` + `transformers` + CPU-only `torch` (ADR-0015), `langchain-anthropic` + `langchain-core` (ADR-0016), `celery` (fixed stack), plus **not covered by any ADR**: `pgvector` (Python SQLAlchemy `Vector` type; alternative is a hand-written `UserDefinedType`), the MinIO client (P-2), and a MIME lib only if P-1 picks B/C.
- **P-9 bge-m3 pinned revision.** The commit hash must be looked up on HuggingFace at implementation time and stored in config/`embedding_configs`. Ask: human confirms the hash (or authorises the implementer to resolve and record the current `main` commit in the plan as a deviation note).
- **P-10 "Notify the Teacher" on a dropped cycle edge (FR-CUR-002/Section 37).** `Notification` is Phase 9 (FR-NOT-001). Recommend: persist the flag, return it in the graph response, show the Section 37 banner in the review UI, defer persistent notification rows to Phase 9. Alternative: add a minimal Notification table now (scope creep).
- **P-11 ApprovedResourceLink "Topic" reference.** FR-CON-001 input is "Teacher-authored Topic/title metadata" but Topics do not exist until 2B's curriculum is active. Recommend: store free-text `topic_label` plus optional `unit_id`; linking to stable Topic IDs happens in the recommendation phase (Phase 9, FR-REC-001).
- **P-12 Upload size enforcement and HTTP status.** Reject over 25 MB while streaming to a spooled temp file (never buffering unbounded memory); return `400` with a clear message (Phase 1 maps no 413), or add a 413 mapping. Recommend 413 (new entry in the error map) plus a documented reverse-proxy limit.
- **P-13 Plan-level interpretations to confirm (low risk, easy to change):**
  - A-1 "Assigned Teacher for a Subject" means assigned to any SubjectInstance of that Subject; unassigned => non-enumerating 404, assigned non-Owner => 403.
  - A-2 One SYLLABUS asset per Subject (new syllabus = new version of that asset), so "the ACTIVE syllabus ContentVersion" is unambiguous; other types allow many assets.
  - A-3 Upload `content_type` is chosen from the five `chunk_type` values (`syllabus|notes|ppt|pyq|lab`) so `chunk_type` is set by the Teacher, not inferred from file extension.
  - A-4 A DRAFT CurriculumVersion is a mutable working copy with a `revision` counter (each edit audited, validation rerun, `validated_revision` must equal `revision` to approve); it becomes immutable at ACTIVE (service guard + test, plus DB-level rule rejecting UPDATE of ACTIVE topic rows is out of scope). Alternative: a new version row per edit (version explosion).
  - A-5 FR-CUR-003's edit list plus Section 18's "assigned or removed" for orphans => Teacher may also delete a Topic (G12).
  - A-6 Cross-subject edges may only target Topics in an ACTIVE CurriculumVersion of an earlier-semester Subject in the same Program; the edge pins that exact version.
  - A-7 Generation allowed for LAB-type Subjects too (BUS-042 excludes only planning).
- **P-14 LangGraph in Phase 2?** Retry-with-repair is a small bounded loop. Recommend plain `langchain-anthropic` + Python loop in `curriculum_agent.py` now, introducing `langgraph` when a multi-step chain appears (Phase 3 Assessment -> Critic). Alternative: use LangGraph now for the generate/repair/persist chain. Fixed stack allows either.
- **P-15 Live LLM cost/safety.** The `llm_live` smoke test and the demo run need `ANTHROPIC_API_KEY` from env (never committed) and cost under about US$1 per run (ADR-0016 estimate). Confirm the demo host has outbound access (ASM-004).

## Approval

- [x] Approved by human reviewer (slice 2A 2026-10-02; slice 2B 2026-10-04)
- Date approved: 2026-10-02
- Notes (recorded 2026-10-04 from the human's answers in the working session):
  - 2026-10-02: "Plan approved. Implement slice 2A (Ingestion) only." For the open items affecting 2A, the human accepted every recommendation in this plan as written: P-1 (A), P-2 (`minio` SDK + `minio/mc` one-shot `minio-init`), P-4 (proposed numbers; any non-blank failing page fails the version), P-5 (ingest notes as `slide:<n>#notes`), P-6 (recommended rule; see the 2026-10-04 decision below for the open NULL question), P-8, P-9 (implementer resolves and records the bge-m3 hash), P-11, P-12 (413), P-13 A-1..A-3. R-4: acceptance of ADR-0015 is the explicit sign-off for CPU-only torch + sentence-transformers.
  - 2026-10-04 decisions after the slice 2A verification (findings B1..m9):
    - B2: libraries recorded in ADR-0019 (minio, pgvector, minio/mc, Pillow); numpy removed as a direct dependency.
    - P-6 / m2: a non-syllabus upload must choose one Unit or "All units". An "All units" upload with no matching Unit headings fails like a syllabus does. Only syllabus or "All units" text before the first heading may have `unit_no = NULL`, and it is flagged.
    - M2: any assigned Teacher may retry a PENDING version at once, or a RUNNING version once it has not updated for longer than a configurable timeout (default: job time limit + 10 minutes). The UI offers Retry in both cases; the retry is audited.
    - M5 defaults (configurable): job time limit 30 min (soft limit 25 min), at most 500 PDF pages, PPTX/DOCX at most 200 MB uncompressed, compression ratio at most 100:1, at most 2,000 archive members.
  - 2026-10-04 (relayed from the human): "Slice 2A is accepted." Honest caveat: 2A's 155 Docker-backed tests (pg/minio/tesseract/hf_model) have NOT been run (no Docker on this machine; they run later on the user's other PC).
  - 2026-10-04: implement slice 2B now. For every open item affecting only 2B the human accepted the plan's recommendation as written: P-3 (provider-neutral interface + Anthropic adapter now; OpenAI adapter a named Phase 3 follow-up, with stub contract tests for the interface now), P-7 (~60 labelled pairs in `backend/tests/fixtures/duplicate_pairs.json`, real bge-m3 via the validation script; VALIDATED only if precision >= 0.90 and recall >= 0.80; report in `similarity_thresholds.validation_report`), P-10 (persist the flag, return it in the graph response, show the Section 37 banner; persistent Notification rows deferred to Phase 9), P-14 (plain `langchain-anthropic` + bounded Python repair loop; no LangGraph in Phase 2), P-15 (`ANTHROPIC_API_KEY` only from the environment, never committed), A-4 (DRAFT CurriculumVersion is a mutable working copy with a revision counter; `validated_revision` must equal `revision` to approve; immutable at ACTIVE), A-5 (Teacher may delete a Topic), A-6 (cross-subject edges only to Topics in an ACTIVE CurriculumVersion of an earlier-semester Subject in the same Program, pinning that exact version), A-7 (generation allowed for LAB Subjects).
  - 2026-10-04: no live LLM calls on the implementing machine. All tests use a fake LLM/adapter; the single `llm_live` smoke test is written, skips unless `ANTHROPIC_API_KEY` is set, and was not run.

## 2B: As-built record (deviations from the 2B plan, recorded 2026-10-04)

**Files not created or merged**
- `test_topic_duplicate_pgvector.py` and `test_similarity_threshold.py`(PG half): duplicate detection from stored vectors is covered in `test_curriculum_service.py` (`test_duplicates_flagged_visibly_but_do_not_block`, `test_validation_records_embedding_config_and_threshold_ids`); the pure threshold rules are in `tests/unit/test_similarity_threshold.py`.
- Vitest: the planned six files are consolidated into `TeacherCurriculum.test.tsx` (8 tests).
- `llm_live` test lives in `tests/integration/test_curriculum_live.py`; `test_duplicate_threshold_validation.py` is the `hf_model` test.

**Files added that the plan did not list**
- `app/services/ai_config_service.py` (provider-config versioning), `app/services/threshold_validation.py` (pure acceptance rule for P-7), `app/agents/curriculum_runner.py` (joins agent output to the deterministic services and writes `agent_runs`), `tests/support/llm.py`, `tests/support/curriculum_helpers.py`, `tests/unit/test_deterministic_boundary.py` (static + clean-interpreter import check).

**Behaviour decided while building**
- `similarity_thresholds.status` also has `RETIRED` (a replaced ACTIVE threshold). A threshold becomes ACTIVE only from VALIDATED (CHECK requires `validated_at`); approval requires the version's threshold to be ACTIVE for its embedding configuration, so the initial DRAFT 0.92 blocks approval until `validate_similarity_threshold --activate` passes.
- Duplicate Topic pairs and dropped cycle edges are flagged for Teacher visibility but are not approval blockers; orphans and a remaining cycle are. An edge a Teacher adds that closes a cycle is resolved by the same drop rule (so `test_add_edge_triggers_revalidation_and_new_cycle_blocks_approval` became `test_add_edge_creating_a_cycle_drops_lowest_confidence_and_flags`); approval additionally re-checks orphans and cycles from stored rows.
- A RETURNED (rejected) version is editable and reverts to DRAFT on the first edit; fallback is only available when no ACTIVE curriculum exists.
- Flat fallback: one Topic per Unit, hours from `fallback_topic_est_hours` (1.0), no edges, created directly ACTIVE.
- Merge sums est_hours and unites outcomes; split deletes the original's edges and each part states prerequisites/dependents explicitly.
- Agent output may carry `prior_topic_id` so Topic ids stay stable across regenerated versions; `ext:<topic id>` refs carry cross-subject prerequisites.
- Prompt sync runs in the FastAPI lifespan and on Celery `worker_init`; tests turn it off for SQLite apps via `PROMPT_SYNC_ON_STARTUP=false` (conftest) and test `sync_prompts` directly.
- Spike S-1 NOT performed (no key, no live calls): the adapter sends `output_config={effort, format: json_schema}` through `ChatAnthropic(model_kwargs=...)` with no tools, no `tool_choice` and no sampling parameters; the exact pass-through name must be confirmed by the first `llm_live` run. `langchain-core`/`langchain-anthropic` are declared in pyproject but are not installed in this machine's venv (the adapter imports them lazily).
- Migration 0003 was written against the models by hand and has never run on PostgreSQL.
