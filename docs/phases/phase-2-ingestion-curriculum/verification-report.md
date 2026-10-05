# Phase 2 - Ingestion & Curriculum - Verification Report

## Phase

- Phase number: 2
- Phase name: Ingestion & Curriculum (FR-CON-001..004, FR-CUR-001..004)
- Plan reference: docs/phases/phase-2-ingestion-curriculum/plan.md
- Verified: 2026-10-05, branch `phase-2-ingestion-curriculum`, all work uncommitted vs HEAD d0f13c9
- Verifier: implementation-verifier-shipper (did not modify any code, test, ADR, plan or CLAUDE.md)

## Overall Verdict

**PASS WITH NOTES** (re-verified 2026-10-05 after fixes; initial verdict was BLOCKED on D1 and D2, both now closed). Ready to ship once the human accepts the open items below (S-1 live-LLM request shape unverified, Docker build not run, MinIO archived-upstream risk).

Justification: the initial run found two confirmed defects (D1 generation stuck in GENERATING, D2 explicit null in PATCH gives 500). The main session fixed both; I re-read the code and re-ran the affected tests (73 passed, below). The main session full suite after the fixes: 717 passed, 0 failed, 1 deselected (llm_live), coverage 95%, so Phase 1 regression remains clean. No remaining code defect is known. What was NOT verified: the live LLM call (S-1) and the Docker build, both by human decision or machine limits.

NOT executed (explicit):
- The live LLM call (`-m llm_live`, tests/integration/test_curriculum_live.py): human chose the stub, no ANTHROPIC_API_KEY. Spike S-1 stays unverified.
- The Docker image / compose build (no Docker); backend/Dockerfile, docker-compose.yml and .github/workflows/backend-tests.yml are unbuilt/unrun.
- I did not re-run the full 698-test suite, Vitest, ruff or mypy; those are the main session recorded results.

## Environment

- WSL Ubuntu user space: PostgreSQL 15.19 + pgvector 0.5.1 (localhost:5432), Redis 8.10, MinIO (9000; app + test scoped users), Tesseract 5.5.3, Python 3.11.16 with CPU torch, sentence-transformers, langchain-anthropic; real BAAI/bge-m3.
- Windows side: Python 3.12 venv (ruff/mypy), Node/Vite/Vitest.
- Stub LLM only (human decision).
- Differences from target: pgvector 0.5.1 vs the newer compose image; Python 3.12 Windows venv vs 3.11 target (3.11 used for authoritative runs).

## Commands and real results

| What | Command | Result | By |
|---|---|---|---|
| Full backend suite incl. Phase 1 | `wsl_tests.sh -m "not llm_live" --cov=app` | 698 passed, 0 failed, 1 deselected (llm_live). Coverage 95%; ingestion_service 97%, curriculum_graph 99%, threshold_validation 100%, curriculum_service 96%, curriculum_edit_service 93%, content_service 99%; all app/services >= 84% | main session |
| Spot check | `wsl_tests.sh tests/integration/test_curriculum_service.py test_curriculum_api.py test_phase2_demo_flow.py test_verification_fixes.py -q -m "not llm_live"` | progress output 72 + 11 = 83 dots, no F/E, no Traceback/FAILED. The "N passed" summary line was not captured (-q plus coverage table), so "83 passed, 0 failed" is inferred from the dots. | verifier |
| Frontend | vitest, tsc -b | 59/59 passed (9 files), tsc clean | main session |
| ruff | | only project-wide UP042 style (Phase 1 convention) + one pre-existing Phase 1 E501 (tests/integration/test_student_import_api.py) | main session |
| mypy | | 21 pre-existing errors, Phase 1 files only; none in Phase 2 files | main session |
| verify-live Part 1 | `audit_phases.py 2` | all 8 IDs found, no gaps (report was missing then; now written) | main session |
| Migrations | 0001->0002->0003 on real PostgreSQL; round-trip tests | pass; MinIO bootstrap idempotent | main session |
| Plan test-name existence | script over file.py::test_name in plan.md | 71 names; all exist except 5 renamed (equivalents listed below) | verifier |
| Secret scan | grep tracked files; git check-ignore | no real keys; .env and backend/.env ignored; only .env.example tracked | verifier |

## Phase 1 regression

- The 698-test run includes all Phase 1 tests and passes; Phase 1 files touched by Phase 2 (alembic/env.py, core/config.py, deps.py, errors.py, main.py, models/__init__.py, conftest.py, docker-compose.yml, frontend App.tsx + test) are covered by it and by the 59 Vitest tests.
- Phase 1 live: Admin login, Hierarchy, Teachers and Owners pages render, no console errors (main session).
- Phase 1 behaviour issue found and fixed by the main session: alembic fileConfig(disable_existing_loggers=False) (the Section 37 denial log was silenced). Phase 1 seed untouched; new scripts/seed_phase2_demo_roles.py uses the real Phase 1 services.
- Dependency integration (Phase 1 SubjectInstances/Teachers): Owner/CO/assignment checks go through Phase 1 SubjectOwnerAssignment and teacher assignments; proven by test_content_service.py:302 (authorization matrix), the demo flow, and the live run with the Phase 1 seeded teachers.

## Requirement-by-requirement verification

Legend: RUN = executed (real services / unit / live); UNTESTED; MISSING; DEVIATES. Tests under backend/tests/. Assigned = assigned Teacher (others get 404, logged); Owner = Subject Owner (assigned non-owner gets 403, logged). Routes: app/api/routes/teacher_content.py (C1-C13), teacher_curriculum.py (G1-G15).

### FR-CON-001 Shared Subject Content Upload

| Verb | Endpoint / guard | Service / UI | Tests | Status |
|---|---|---|---|---|
| upload PDF/PPTX/DOCX/TXT up to 25 MB | C2 POST /teacher/subjects/ID/content/uploads, Assigned, rate-limited | content_service; ContentUploadForm | integration/test_content_api.py:94; unit/test_upload_validation.py:44 (exact 25 MB ok, +1 rejected) | RUN |
| register HTTPS link | C10, Assigned | resource_link_service; ResourceLinks | test_content_api.py:384; test_resource_link_service.py:21 | RUN (live) |
| extension / actual MIME | C2 | upload validation | test_content_api.py:115,123; unit/test_mime_detection.py; unit/test_upload_validation.py:21 | RUN |
| size | C2 (ASGI body cap core/body_limit.py) | | test_content_api.py:135 (413, no rows) | RUN |
| non-empty | C2/C10 | | test_content_api.py:145; unit/test_upload_validation.py:50; test_resource_link_service.py:79 | RUN |
| HTTPS only | C10 | client + server | test_content_api.py:403; test_resource_link_service.py:57,63 (DB CHECK) | RUN (live) |
| Subject assignment | C2/C10 | picker from C1 | test_content_api.py:152,417; test_content_service.py:136 | RUN |
| DRAFT version/resource, pending ingestion | C2/C10 | DRAFT badge | test_content_service.py:73,86,94 | RUN |
| links not crawled/embedded | C10 | | test_resource_link_service.py:36,49 | RUN |
| active content unchanged | C2 | | test_content_service.py:106 | RUN |
| Unit or All units required (added) | C2 | Unit selector | test_verification_fixes.py:259 | RUN (live) |

### FR-CON-002 Deterministic Ingestion (AC-004)

| Verb | Where | Tests | Status |
|---|---|---|---|
| validate, OCR, clean, chunk (max 800 tokens, overlap 120, no Unit crossing), embed, store | Celery ingest_content_version; services/ingestion_service.py, services/ingestion/ | unit/test_chunking.py:27,43,65,122; unit/test_ingestion_service.py:64,73,115; integration/test_ingestion_e2e.py:55 (AC-004 positive, real Tesseract/MinIO/bge-m3) | RUN |
| empty/unreadable fails clearly, no empty chunks | worker | unit/test_ingestion_service.py:98,162; test_ingestion_e2e.py:88 (AC-004 negative) | RUN |
| retry/resume, idempotent | C5 POST .../retry, Assigned | unit/test_ingestion_service.py:220,232; test_content_api.py:239; test_verification_fixes.py:136-203 | RUN |
| page/unit association | chunker | unit/test_chunking.py:83,93; unit/test_unit_boundaries.py | RUN |
| stage status recorded | worker | unit/test_ingestion_service.py:73; test_content_api.py:206 | RUN |
| retrievable only in correct scope | services/content_retrieval.py (no endpoint; Phase 8 consumer) | integration/test_content_retrieval_scope.py (9) | RUN |
| partial failure not approved | | test_content_service.py:340,460 | RUN |

Renamed in as-built vs plan (equivalents exist, not defects): test_chunk_rows_are_insert_only -> unit/test_chunk_immutability.py + test_verification_fixes.py:119; test_oversize_rejected_before_full_buffering -> test_content_api.py:135; test_rejects_legacy_doc_ppt_exe_and_images -> unit/test_upload_validation.py:21; OCR adapter tests -> unit/test_ingestion_service.py:115-139; test_topic_duplicate_pgvector -> test_curriculum_service.py:378.

### FR-CON-003 Chunk Metadata and Traceability

| Verb | Where | Tests | Status |
|---|---|---|---|
| store subject_id, content_version_id, unit_no, source_file, locator, chunk_type | worker STORE; models/content.py | integration/test_chunk_store.py:56 | RUN |
| immutable reference resolves after supersede | C7 GET /teacher/content/chunks/ID, Assigned | test_content_api.py:289,319; test_content_service.py:410 | RUN (live Resolve citation) |
| locator not null | DB CHECK + chunker | test_chunk_store.py:114,129; unit/test_locators.py | RUN |
| links create no chunks | C10 | test_resource_link_service.py:36,49 | RUN |
| AI output traceable | topic source refs | test_curriculum_service.py:117 | RUN |
| vectors never exposed | C6 | test_content_api.py:264 | RUN |

### FR-CON-004 Versioning, Activation, Rollback (AC-005)

| Verb | Endpoint / guard | Tests | Status |
|---|---|---|---|
| immutable DRAFT, write-once file | C2 | test_content_service.py:73; integration/test_minio_store.py | RUN |
| DRAFT link, revision | C10/C13 | test_resource_link_service.py:125,140; test_verification_fixes.py:284,291 | RUN (live) |
| Owner activates; v1 SUPERSEDED but traceable (positive) | C8 POST .../versions/ID/activate, Owner | test_content_service.py:270 | RUN (live) |
| CO / unassigned rejected (negative) | C8, C9, C12 | test_content_service.py:282 (403), 293 (404), 302 (matrix); test_content_api.py:334,363,428; test_verification_fixes.py:317,356 | RUN |
| rollback | C9, Owner | test_content_service.py:361,377,394 | RUN (live) |
| approve link | C12, Owner | test_resource_link_service.py:94,107 | RUN (live) |
| no in-place edit | no PUT/PATCH/DELETE | test_content_api.py:480,489 | RUN |
| atomic | row lock + partial unique index | test_content_service.py:478,501 | RUN |
| audit same txn | | test_content_service.py:244 | RUN |
| needs successful ingestion | | test_content_service.py:340,460; test_content_api.py:351 | RUN |

### FR-CUR-001 Curriculum Version Extraction

| Verb | Endpoint / guard | Service / agent | Tests | Status |
|---|---|---|---|---|
| request generation | G1 POST /teacher/subjects/ID/curriculum/generate (202), Assigned, rate-limited, 409 without active syllabus | curriculum_service request path (~line 160); Celery curriculum_tasks | test_curriculum_api.py:40,51,60,67; test_curriculum_service.py:61,77,85 | RUN |
| strict schema, repair, refusal, outage | | agents/curriculum_agent.py; schemas/curriculum_agent.py | unit/test_curriculum_agent.py; test_curriculum_service.py:140,152,160 | RUN (stub) |
| stable IDs, outcomes, Bloom, hours, edges 0..1 | | persist in curriculum_service | test_curriculum_service.py:94,187 | RUN |
| inherited Unit weightage | | derived, not stored | test_curriculum_service.py:107 | RUN |
| earlier-semester cross-subject scope | | | test_curriculum_service.py:207,221,241 | RUN |
| ACTIVE stays available | G3 | | test_curriculum_service.py:130 | RUN |
| agent_runs logging (NFR-AI-002) | | agents/curriculum_runner.py:66 | integration/test_agent_runs_logging.py | RUN (stub) |
| real Anthropic request | | integrations/llm/anthropic_adapter.py | unit/test_llm_provider_contract.py (fake factory only) | UNTESTED live (S-1) |
| fails safely in all paths | | curriculum_tasks.py wraps the whole body; stale/queue-failure handling in curriculum_service | unit/test_curriculum_failsafe.py (15); test_curriculum_service.py (queue failure, live 409, stale, agent-run close) | RUN (D1 closed) |

### FR-CUR-002 Graph Validation (AC-006)

| Verb | Where | Tests | Status |
|---|---|---|---|
| DFS cycle; drop lowest-confidence edge; flag | services/curriculum_graph.py (pure) | unit/test_curriculum_graph.py:41,46 (0.8 / 0.4, drops 0.4, acyclic) | RUN |
| tie: ascending normalized (topic_id, prereq_topic_id), remove first | curriculum_graph.py:117-120 | :54,60,67 | RUN |
| repeat until acyclic; self-loop | | :80,93,109 | RUN |
| orphans | | :139; integration test_curriculum_service.py:313 (AC-006 negative) | RUN |
| duplicates strictly above threshold, same embedding config only | curriculum_graph.py:190-205 | :160,169,178,191; integration :378 | RUN |
| versioned config/threshold; unvalidated cannot activate | similarity_config_service, threshold_validation | test_curriculum_service.py:330,341,362; unit/test_similarity_threshold.py | RUN (real bge-m3 validation, ADR-0020) |
| remaining cycle blocks approval (negative) | | test_curriculum_service.py:444 | RUN |
| validate endpoint | G5, Assigned | test_curriculum_service.py:401 | RUN |

Sections 23-25 diff: Phase 2 does not touch those scoring formulas. I diffed the FR-CUR-002 rules (lowest confidence, ascending normalized tie-break, repeat until acyclic, strict greater-than) against curriculum_graph.py:117-120 and :190-192: exact match. The threshold value 0.72 differs from the SRS initial 0.92 under approved ADR-0020 (real bge-m3 caught 0/30 duplicates at 0.92).

### FR-CUR-003 Teacher Graph Editing

| Verb | Endpoint / guard | Tests | Status |
|---|---|---|---|
| rename/classify/hours/outcomes/Bloom/assign Unit | G6 PATCH .../topics/ID, Assigned, DRAFT/RETURNED only | integration/test_curriculum_edit.py:62,119,133,164,178,411 | RUN (live: ACTIVE gives 409) |
| merge / split with mappings | G7, G8 | :192,217,241 | RUN |
| reorder | G9 | :280 | RUN |
| add / delete edge | G10, G11 | :304,333,356,380 | RUN |
| remove topic | G12 | :395 | RUN |
| save + revalidate; approval stays pending | every edit | :78,105; test_curriculum_service.py:454 | RUN |
| CO may edit; unassigned 404; ACTIVE 409 | | :445,475,499; test_curriculum_api.py:239 | RUN |
| explicit JSON null in PATCH | G6 | unit/test_curriculum_failsafe.py; test_curriculum_api.py (422 for name, unit_id, est_hours, outcomes) | RUN (D2 closed) |

### FR-CUR-004 Owner Approval and Fallback (AC-007)

| Verb | Endpoint / guard | Tests | Status |
|---|---|---|---|
| approve gives ACTIVE, prior SUPERSEDED traceable (positive) | G13, Owner; curriculum_service.py:698 (require_owner, subject lock, blockers) | test_curriculum_service.py:412; test_curriculum_api.py:130,265 | RUN |
| CO approval blocked; remaining cycle blocked (negative) | G13 | test_curriculum_service.py:429,444,463; test_curriculum_api.py:309 | RUN (live) |
| reject gives RETURNED, prior unchanged | G14 | test_curriculum_service.py:470; test_curriculum_api.py:288 | RUN |
| flat fallback only if no ACTIVE, Owner, no edges | G15 | test_curriculum_service.py:485,497,508,518 | RUN (live) |
| audit + atomic pointer | | test_curriculum_service.py:528,547,581 | RUN |
| active version for later phases | G3 | test_curriculum_service.py:565 | RUN |

## Live verification log (main session; I did not re-drive the UI)

CO teacher UI: My Subjects, CS301 content, Unit choice incl. All units, syllabus v1 ACTIVE, 7 ingestion stages SUCCEEDED, chunk table, Resolve citation, http link rejected client-side, https link saved DRAFT, no Activate/Rollback/Approve controls. API as CO: 400 without Unit, 201 with Unit, real Celery ingestion PENDING, RUNNING, SUCCEEDED. Owner: activate, approve link, revise, syllabus v2 upload/ingest/activate (v1 SUPERSEDED), UI rollback (v1 ACTIVE). Curriculum tab without API key: GENERATION_FAILED with agent_run recorded; Owner flat fallback with reason gives ACTIVE; PATCH on ACTIVE gives 409. Phase 1 pages render with no console errors. Limit: GIF export timed out; evidence is text/API output.

## Section 43 Expected Demo

Bar: feed cyclic syllabus; CO edits but cannot activate; Owner activates corrected graph; prior active chain remains resolvable.

| Clause | Code | Test | Live |
|---|---|---|---|
| cyclic graph repaired | curriculum_graph drop + flag | integration/test_phase2_demo_flow.py:23 | lowest-confidence edge (0.400) dropped to break the cycle |
| CO edits | curriculum_edit_service | test_phase2_demo_flow.py:23; test_curriculum_edit.py:445 | CO Teacher edited a Topic |
| CO cannot activate | require_owner gives 403, logged | test_curriculum_service.py:429 | Only the Subject Owner can perform this action (denial logged) |
| Owner activates corrected graph | approve_version | test_phase2_demo_flow.py:23 | Owner approved; curriculum ACTIVE |
| prior chain resolvable | SUPERSEDED retained; G2/G4/C7 | test_phase2_demo_flow.py:49; test_curriculum_service.py:565 | Prior active v2 is now SUPERSEDED and still resolvable (4 Topics) |

Caveat: the demo uses the stub LLM, so the extraction step proves the pipeline from stub output onward, not the real model extraction quality.

## AI-vs-deterministic boundary checklist

| Item | Result | Evidence |
|---|---|---|
| No LLM/agent/prompt imports in deterministic code | PASS | unit/test_deterministic_boundary.py:52 (AST), :61 (clean interpreter), :77. My grep: imports of app.agents, app.prompts, langchain, anthropic exist only in agents/, prompts/, integrations/llm, main.py:72, workers/celery_app.py:36, workers/curriculum_tasks.py:13,17 |
| Cycle drop + tie-break per SRS | PASS | curriculum_graph.py:117-120; tests under FR-CUR-002 |
| Strict greater-than threshold; versioned config; same-config only | PASS | curriculum_graph.py:190-205; tests :169, :178 |
| Orphans block approval | PASS | test_curriculum_service.py:313 |
| Flat fallback Owner-only, no edges, no ACTIVE | PASS | test_curriculum_service.py:485-518 |
| LLM output never alters deterministic results | PASS | agent output is schema-validated into a DRAFT; validation, ordering and thresholds run afterward in pure code; no LLM pass over service output |
| Prompts only in versioned registry | PASS | app/prompts/ synced to immutable prompt_versions with hash check (ADR-0017); unit/test_prompt_registry.py |
| agent_runs logged (NFR-AI-002) | PASS (stub) | agents/curriculum_runner.py:66; integration/test_agent_runs_logging.py |
| Owner gates | PASS | require_owner: curriculum_service.py:705,746,775; content_service.py:433 |
| Real Anthropic request shape | NOT VERIFIED | S-1 |

## Code review (agent-skills:code-reviewer, read-only; verdict REQUEST CHANGES, no Critical)

Confirmed by me against the code:

- D1 (Important, CONFIRMED by code read, blocking; FR-CUR-001 fails safely, NFR-REL-001): a generation can stay GENERATING forever.
  - backend/app/services/curriculum_service.py:166-172: any GENERATING row makes a new request fail with already being generated; no staleness window. Lines 195-198 swallow an enqueue failure and leave the row GENERATING.
  - backend/app/workers/curriculum_tasks.py:44-58: generate_curriculum has no try/except around build_provider and run_generation; a provider-config error, prompt-registry error or SoftTimeLimitExceeded leaves the version GENERATING and the agent_run RUNNING.
  - backend/app/workers/celery_app.py:24-25 applies the ingestion limits (soft 25 min, hard 30 min; config.py:73-74) to this task as well. The reviewer cites an LLM timeout of 600 s with up to 3 calls (config.py:98; I did not check that line), which can reach the limit.
  - Effect: the Subject cannot generate again; the flat fallback works only when no ACTIVE curriculum exists. No test covers it. I did not execute a repro.
  - Fix: own time limits for the task; catch Exception including SoftTimeLimitExceeded and call mark_generation_failed; stale-GENERATING window or on_failure hook; tests.
- D2 (Important, CONFIRMED by code read, not executed): PATCH topic with explicit JSON null (for example name null). TopicPatch fields are optional (schemas/curriculum.py:169-174), the route uses model_dump with exclude_unset (teacher_curriculum.py:180) which keeps the null, and _clean_name(None) calls name.strip() (curriculum_edit_service.py:130-131); est_hours, outcomes and unit_id nulls are similarly dereferenced (db.get(Unit, None) at :155-156). Result: HTTP 500 instead of 400. Fix: reject or drop null-valued keys; add a test per field.
- D3 (Important, unverified by design): S-1, build_chat_kwargs passes model_kwargs output_config through langchain-anthropic (anthropic_adapter.py:12,49-56); if dropped or rejected, every real generation fails. Unit tests with a fake factory cannot detect it.

Reviewer suggestions (not individually re-verified; none blocking): row lock held across MinIO upload of up to 25 MB (content_service.py:200,241); quadratic pure-Python duplicate detection, no max on agent draft topics (curriculum_graph.py:195-205); bge-m3 loaded in the web process and validate endpoint not rate-limited (core/deps.py); N+1 queries (list_assigned_subjects, list_assets, build_graph_view); no pixel cap on OCR page render (parsers/pdf.py:42); core/deps.py imports from services; wrong wording of the validate conflict message for RETURNED versions; Dockerfile runs as root while the worker parses untrusted files; MinIO dev defaults in compose; ACTIVE curriculum immutability only service-layer (no DB trigger).

Reviewer found clean: query-level authorization with non-enumerating 404 and 403 only for assigned non-owners; UUID-only object keys; content-based MIME with zip-bomb limits; links never fetched; no committed secrets; no MinIO root fallback.

## ADR compliance (0001-0020) and security

- 0001 JWT cookie + CSRF: PASS (test_content_api.py:82, test_curriculum_api.py:85).
- 0002/0003 weight service layer, single Owner: PASS (Owner via SubjectOwnerAssignment; weightage derived from Unit).
- 0006 rate limit: PASS for upload and generate (test_content_api.py:181, test_curriculum_api.py:67); validate not limited (suggestion).
- 0009 VARCHAR + CHECK: PASS (test_verification_fixes.py:64,75).
- 0010/0019 supporting libraries: PASS; no unlisted infrastructure seen.
- 0011 audit every mutation: PASS (test_content_service.py:244, test_curriculum_service.py:528, test_curriculum_edit.py:514).
- 0013/0014/0015 Tesseract, parsers, bge-m3 vector(1024): PASS (real services in test_ingestion_e2e.py, HF tests).
- 0016 Anthropic adapter, claude-opus-5-5: present; live behaviour unverified (S-1).
- 0017 prompt registry, 0018 MinIO layout: PASS. 0020 threshold 0.72: PASS (default 0.720, validated, activated with report).
- 0004, 0005, 0007, 0008, 0012: not affected by Phase 2.
- Security: no secrets committed; .env is git-ignored; .env.example has placeholders only (header still says Phase 1: Foundation, cosmetic). CI workflow uses test-only minioadmin and generated secrets; I did not touch the .github folder.

## Open items

1. S-1 langchain-anthropic output_config/effort pass-through unverified (no live LLM by human decision): run the llm_live test with a key or explicitly accept the risk.
2. MinIO open-source upstream archived (dl.min.io returns 410 Gone, no security updates): risk for the fixed stack; needs a human decision (ADR or SRS amendment).
3. .github/skills/phase-status/check.py cannot be written here (EPERM); phase-status false positives for Phases 4 and 9 unfixed.
4. Docker image and compose build never run; native WSL run substituted; Dockerfile unbuilt.
5. pgvector 0.5.1 vs newer in compose image; Python 3.12 Windows venv vs 3.11 target.
6. One llm_live test deselected by human decision.
7. Plan-vs-as-built test renames (listed under FR-CON-002).

## Re-verification after fixes (2026-10-05)

Command (verifier, WSL Python 3.11, real PostgreSQL/pgvector, MinIO): `wsl_tests.sh tests/unit/test_curriculum_failsafe.py tests/integration/test_curriculum_service.py tests/integration/test_curriculum_api.py -p no:cacheprovider --no-cov -m "not llm_live"`
Real summary line: `73 passed, 43 warnings in 127.30s (0:02:07)` (warnings are the JWT short-test-key warning).
Main session, after fixes (not re-run by me): full suite 717 passed, 0 failed, 1 deselected, coverage 95%; Vitest 59/59; tsc clean; ruff only UP042 + pre-existing Phase 1 E501; mypy 21 pre-existing Phase 1 errors.

- D1 CLOSED (read in code):
  - core/config.py:109-130: new curriculum_task_soft/hard limit and stale settings; effective soft = llm_request_timeout x (1 + llm_repair_attempts) + 300 s, hard = soft + 300 s, stale = hard + 1200 s (matches the stated 2100/2400/3600 with a 600 s timeout and 2 repairs).
  - workers/curriculum_tasks.py:72-73 task-specific soft_time_limit and time_limit; :87 Retry re-raised; :89-97 SoftTimeLimitExceeded anywhere in the chain (_caused_by_time_limit, :49-53) gives GENERATION_FAILED with TIME_LIMIT_MESSAGE, any other exception gives GENERATION_FAILED with UNEXPECTED_MESSAGE.
  - services/curriculum_service.py:173-180 a live GENERATING version blocks with a 409 stating when it becomes stale (generation_stale_at, :221-232); a stale one is marked failed (STALE_GENERATION_MESSAGE) and a new version starts; :207 enqueue failure marks the new version failed (QUEUE_FAILED_MESSAGE). The main session states mark_generation_failed now closes RUNNING agent_runs; I rely on its test (test_curriculum_service.py) for that, which passed.
- D2 CLOSED (read in code): schemas/curriculum.py:176-182 TopicPatch model_validator rejects any field set to null (422); services/curriculum_edit_service.py:179 rejects null values with ValidationError (400) before touching the DB. Tests: test_curriculum_failsafe.py and test_curriculum_api.py (422 for the four fields).
- Phase 1 impact: the main session reverted a ruff-format reformat of a Phase 1 line in config.py; only intended Phase 1 change is removal of unused minio_access_key/minio_secret_key settings. Covered by the 717-test run (not re-run by me).

## Blocking Issues

None. (Initial D1 and D2 closed as above.) Open items 1, 2 and 4 need human acceptance but are not code defects.

## Exact remaining steps before shipping

1. Human accepts or resolves: S-1 (run llm_live with a key, or accept), MinIO archived-upstream risk, Docker build not run.
2. Only after a fresh go-ahead in the conversation: branch, commit, push, PR (nothing committed or pushed so far).

## Shipment Record

Not shipped. No branch change, commit, push, PR or gh invocation.

- Branch: `phase-2-ingestion-curriculum` (stacked on `phase-1-foundation`, PR #1)
- Commit(s): `3537d8e` (Phase 2), `00df905` (mark shipped), `8df04ce` (MinIO image / CI fix, ADR-0021)
- PR URL: https://github.com/leeshaparab1922-crypto/uniadaptfake/pull/2
- Shipped at: 2026-10-05 (open notes S-1 and MinIO accepted by the project owner)

## Post-ship CI verification (2026-10-05)

- **First CI runs** (`3537d8e`, `00df905`) failed before any test ran: `pull access denied for minio/minio`. The official MinIO images have been removed upstream.
- **Fix** (`8df04ce`, ADR-0021, Proposed): `infra/minio/Dockerfile` builds `uniadapt/minio:2025.10.15` from checksum-pinned conda-forge `minio-server` 2025.10.15 and `minio-client` 2025.08.13 packages. `docker-compose.yml` uses it for `minio` and `minio-init`.
- **CI run 37266930599** on `8df04ce`: **success** (job `tests`, 11m13s).
  - Built the backend image: `python:3.11-slim-bookworm`, Tesseract `5.3.0-2` and `tesseract-ocr-eng 1:4.1.0-2` as pinned, CPU PyTorch.
  - Built the MinIO image; the server reports commit `9e49d5e7a648`.
  - Brought up PostgreSQL (`pgvector/pgvector:pg15`) and MinIO, and ran `minio-init`.
  - `pytest -m "not hf_model and not llm_live"` inside the backend image: **713 passed, 5 deselected** (the 4 `hf_model` tests and 1 `llm_live` test, excluded by the workflow; the `hf_model` tests passed locally on real bge-m3). Coverage 96%.
  - Deterministic-service coverage gate: 97% (required ≥ 80%). Passed.
- **Open-item update:** item 4 (Docker image and compose build never run) is **closed** by this CI run. Still open: S-1 (live LLM request shape) and the MinIO archived-upstream risk (now also covered by ADR-0021, which is awaiting acceptance).
