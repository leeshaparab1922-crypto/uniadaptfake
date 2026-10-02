# Phase 1 — Foundation — Verification Report

## Phase

- Phase number: 1
- Phase name: Foundation
- Plan reference: docs/phases/phase-1-foundation/plan.md

## Requirement-by-Requirement Verification

| ID | Expected (from SRS) | Found in implementation | Pass/Fail | Notes |
|---|---|---|---|---|
| FR-AUTH-001 | bcrypt verify; 4h JWT with role + token_version; revoke on logout/deactivation | security.py (bcrypt, PyJWT 4h expiry, no refresh), deps.py::get_current_user (token_version check), auth_service.logout/deactivate_account increment token_version | PASS | test_auth_api.py::test_logout_revokes_session_immediately, test_deactivated_account_cannot_login |
| FR-AUTH-002 | Role/scope resolved before action; Student=self, Teacher=assigned instances/sections, Admin=institution | deps.py::require_role; enrollments.py::my_enrollments scopes by caller's own Student row (query-level, not fetch-then-filter) | PARTIAL | Admin/Student scoping verified (query-level, e.g. enrollments.py:41-50). Teacher-to-assigned-Section scoping has no implementation or test anywhere in the phase - see Blocking Issue 2. |
| FR-AUTH-003 | Admin-only account admin; unique identity; exactly one role; audit on action; deactivated cannot log in | auth_service.create_account/deactivate_account (role check, audit write), models/user.py role enum | PASS | test_role_scope_enforcement_teacher_cannot_reach_admin_routes, test_deactivated_account_cannot_login |
| FR-AUTH-004 | Admin issues single-use invitation/reset tokens (hash-only); throttling; non-enumerating errors | auth_service.issue_invitation/issue_password_reset/consume_*, rate_limit.py, admin_accounts.py | PASS | See note below on Deviation 3 (Admin-only, no public self-service reset) - text-matches FR-AUTH-004's own Pre/Trigger, not a violation, but flagged for explicit human sign-off since it was a documented deviation from the plan's earlier file-list sketch, not yet separately confirmed. test_login_throttled_after_repeated_failures covers throttling; token expiry/reuse covered in test_auth_service.py. |
| FR-ADM-001 | Institute through Section hierarchy; unique codes; positive capacity; Section requires valid path | academic_structure_service.py (all checks present, create_section explicit path-validation) | PASS | test_academic_structure_service.py |
| FR-ADM-002 | Teacher/Owner assignment; TEACHER-role only; exactly one owner; owner PRIMARY somewhere | assignment_service.py (unique-index-backed owner, PRIMARY-somewhere check, audit write per ADR-0003) | PASS | test_assignment_service.py::test_exactly_one_owner_enforced, test_active_instance_requires_teacher |
| FR-ADM-003 | Subject/Unit catalogue; unique code in scope; weights 0..100 summing to 100; elective membership matches type | subject_service.py, ADR-0002 row-lock (skipped only on SQLite, documented) | PASS | test_subject_service.py |
| FR-ADM-004 | DRAFT SubjectInstance; Program/Semester match; at least one Teacher before activation | subject_instance_service.py | PASS | test_assignment_service.py::test_active_instance_requires_teacher |
| FR-ADM-005 | CSV import; row-level atomicity; named per-row errors; no partial records | student_import_service.py (savepoint per row, ADR-0005) | PASS | test_student_import_api.py::test_mixed_valid_invalid_rows_via_api |
| FR-ADM-006 | Auto-enroll; one elective/group within capacity; previewed promotion/transfer; Post: allocation is audited | enrollment_service.py - auto-enroll/elective logic and capacity/idempotency checks all correct; promotion/transfer preview+confirm atomic with student_placement_history | FAIL (partial) | Promotion/transfer is audited via StudentPlacementHistory (actor_id + operation_id + effective_date). Auto-enrollment (auto_enroll_student) and elective assignment (assign_elective) write zero audit trail and the admin routes calling them don't even pass current_user through - see Blocking Issue 1. |
| FR-ADM-007 | Calendar/timetable; start<end; exam-in-window; no overlapping mandatory events | calendar_service.py | PASS | test_calendar_service.py, test_calendar_api.py::test_create_calendar_window_outside_term_rejected, test_timetable_slot_overlap_rejected |
| FR-STU-001 / BUS-001 | Read-only enrollment list; zero mutation endpoint for Student | enrollments.py::my_enrollments (GET-only), admin_router requires ADMIN; frontend MySubjects.tsx renders no mutate control | PASS | test_enrollment_api.py::test_student_sees_own_enrollments, test_student_enrollment_mutation_forbidden; MySubjects.test.tsx |
| BUS-002 | Auto-derived enrollment; exactly one elective per required group within capacity | enrollment_service.assign_elective (idempotent re-select, capacity check, closes prior selection) | PASS | test_enrollment_service.py::test_single_elective_per_group etc. |
| BUS-043 | Exactly ADMIN/TEACHER/STUDENT; one PRIMARY-designated Subject Owner; other assigned Teachers have full ops except final activation | models/user.py role enum; assignment_service.py owner uniqueness | PASS | - |
| BUS-049 | Promotion/transfer previews before confirm; history preserved, not erased | enrollment_service.preview_promotion (zero writes) / confirm_promotion (atomic, StudentPlacementHistory, closes-not-deletes prior enrollments) | PASS | test_enrollment_service.py::test_promotion_preview_no_mutation, test_promotion_confirm_atomic_with_history |
| BUS-042 | LAB is a distinct Subject type, excluded from planning (enforced later) | models/subject.py::SubjectType.LAB, subject_service.SUPPORTED_TYPES | PASS | Enum modeled correctly; planner exclusion correctly deferred to Phase 7 per plan |
| AC-001 | POS: Teacher assigned to Section A sees only Section A students. NEG: same Teacher denied Section B (403/404) | No Teacher-facing data-read endpoint exists anywhere in Phase 1's backend (confirmed via grep for UserRole.TEACHER across app/api and app/services - zero query-scoping logic keyed on Teacher role) | FAIL | Only tested negative-adjacent scenario is "Teacher denied an Admin-only route" (test_role_scope_enforcement_teacher_cannot_reach_admin_routes), which is not the same scenario as AC-001's literal text. plan.md's own Test Plan table explicitly promised test_role_scope_enforcement covering "Teacher sees only assigned Section's students" - this was not delivered. See Blocking Issue 2. |
| AC-002 | POS: auto-enrollment + elective enrollment created once. NEG: Student-attempted enrollment mutation returns 403, no row change | enrollment_service.py + enrollments.py | PASS | test_enrollment_service.py (idempotency), test_enrollment_api.py::test_student_enrollment_mutation_forbidden |
| AC-003 | POS: valid calendar/timetable save. NEG: invalid dates/missing exam window/overlap rejected | calendar_service.py | PASS | test_calendar_api.py (both directions) |
| AC-029 | POS: invitation/login/4h JWT works; revocation on reset/deactivation/logout immediate. NEG: expired/replayed token, excessive attempts, cross-scope ID blocked, no leak | auth_service.py, deps.py, rate_limit.py | PASS | test_auth_service.py, test_auth_api.py::test_logout_revokes_session_immediately, test_login_throttled_after_repeated_failures |
| AC-030 | POS: preview shows conflicts without mutation, confirm is atomic with history. NEG: zero/multiple elective selections or capacity exceeded blocked | enrollment_service.py | PASS | test_enrollment_service.py::test_promotion_preview_no_mutation, test_promotion_confirm_atomic_with_history, capacity-conflict negative test |

**ADR compliance** (all Accepted, all checked against code): ADR-0001 (httpOnly/Secure/SameSite=Strict cookie + double-submit CSRF, verified in security.py/deps.py/frontend client.ts - CSRF correctly not required on the two pre-authentication token-consume routes since no session cookie exists yet to forge) - PASS. ADR-0002 (Unit weight row-lock, skipped only on SQLite, documented) - PASS. ADR-0003 (single owner + audit) - PASS. ADR-0004 (StudentPreference deferred) - PASS (absent from migration as required). ADR-0005 (CSV row-level atomicity) - PASS. ADR-0006 (Redis fixed-window, config-driven limits, shared helper) - PASS. ADR-0007 (CLASS/LAB only) - PASS. ADR-0008 (tooling) - N/A to code. ADR-0009 (VARCHAR+CHECK enums, confirmed in every model and every migration enum column) - PASS. ADR-0010 (Vite/python-dotenv/PyJWT) - PASS.

**Exact-algorithm sections (23/24/25):** Not applicable - confirmed no code in this phase touches Mastery Score, Engagement Score, or the Adaptive Study Planner (matches plan.md's own "Not applicable" call-out).

## Regression Test Results

- Backend: `backend/.venv/Scripts/python -m pytest --cov=app.services --cov-report=term-missing -q` -> **84 passed**, 0 failed. Coverage on app.services: **90%** (exceeds the 80% NFR-TST-001 bar for boundary/failure cases).
- Frontend: `npx vitest run` (in frontend/) -> **3 test files, 10 tests, all passed**.
- No prior "shipped" phases exist yet (Phase 1 is first), so there is nothing to regress against.
- Section 43 dependencies: Phase 1's declared dependency is **None** - confirmed N/A, nothing to integrate against.

### Explicitly unverified (environment-limited) - assessed non-blocking

Docker/Postgres/Redis are not installed in this execution environment, so the following were not exercised live and are traced/read manually instead:

1. **Alembic migration on real PostgreSQL 15.** Not run against a live Postgres instance. Manual trace: table-creation order in 0001_initial_foundation_schema.py is topologically correct for FK dependencies (verified by extracting all 21 create_table calls in order - every FK target table is created earlier in the file, which Postgres requires but SQLite would silently tolerate even if reversed), all sa.Enum(..., native_enum=False, create_constraint=True) per ADR-0009, all timestamp columns use DateTime(timezone=True), all FKs use ondelete="RESTRICT". Verdict: non-blocking. No structural defect found on manual trace; residual risk is limited to things only Postgres itself would catch (e.g. reserved-word collisions, exact CHECK-constraint syntax), a normal bounded residual risk for any migration authored without a live target DB, not a sign of an actual defect.
2. **ADR-0002 SELECT ... FOR UPDATE row lock.** Skipped on SQLite by explicit dialect check (subject_service.py:113-115), applied unconditionally on every other dialect per the code - confirmed by reading the code, not by running a concurrent-write test against Postgres. Verdict: non-blocking. The gating logic is correct and documented; no concurrent-load test exists for either dialect, a coverage gap worth a future phase's attention but not a Phase 1 blocker since ADR-0002's actual invariant (weights sum to 100) is tested under SQLite (test_subject_service.py).
3. **ADR-0009 VARCHAR+CHECK enums.** Actually verified under both test and production paths since native_enum=False behaves identically regardless of dialect - not actually a coverage gap, noted here for completeness.
4. **ADR-0006 Redis fixed-window rate limiting.** Tests inject a FakeRedis implementing only incr/expire, matching RateLimiter's Protocol typing exactly (rate_limit.py:21-24); production always calls get_redis_client() -> real redis.Redis.from_url(...). Verdict: non-blocking. The abstraction boundary is real (typed Protocol, single call site), so the swap-risk is low; no live-Redis fixed-window-boundary-burst test was run, an acceptable known trade-off already called out in ADR-0006 itself ("requests can burst at window boundaries... acceptable").

## Code Reviewer Findings

Delegated to agent-skills:code-reviewer (five axes: correctness, readability, architecture, security, performance). Full findings incorporated below; I independently re-verified its two most material claims by reading the cited files myself.

- **Correctness:** No critical issues. CSRF (Depends(csrf_protect)) and role (Depends(require_role(...))) are applied consistently at router level on every mutating router - independently confirmed by reading all 8 route files myself; found zero missing checks.
- **Security:** (a) backend/app/core/config.py:24 default jwt_secret_key = "change-me-in-env" is a 16-byte placeholder (root cause of the InsecureKeyLengthWarning seen in test output); there is no startup validator rejecting a short/default secret in production. .env.example documents the required override but nothing in code enforces it. (b) Role-scoped queries filter at the DB level, not fetch-then-filter (confirmed independently at enrollments.py:41-50). (c) Generic, non-enumerating error messages used uniformly for auth/token failures (confirmed). (d) No secrets committed - .env.example uses placeholder text, .gitignore excludes .env* except the example - confirmed independently.
- **Architecture:** frontend/src/hooks/useAuth.ts:15-17 mirrors the React Query /auth/me result into a Redux slice (authSlice.ts) via setUser. .claude/rules/frontend.md states plainly: "React Query owns all server state... never duplicate server state into Redux." Confirmed independently by reading both files - this is exactly that duplication, rationalized by an in-code comment but not excepted by the rule. Classified non-blocking (general frontend-architecture convention, not a BUS-*/ADR/NFR-MNT-001/Section-33-34 boundary rule) but should be fixed before this pattern is copied into later phases' role-gated screens.
- **Readability/Performance:** No issues raised.
- **Audit-trail gap (raised independently by the reviewer and by my own SRS trace above - see Blocking Issue 1):** Only auth_service.py's account-lifecycle functions and assignment_service.set_subject_owner write to audit_logs. Every other FR-ADM-002..007 mutation (assign_teacher, create_elective_group/create_subject/set_units, create_subject_instance/activate_subject_instance, CSV import, assign_elective, confirm_promotion, all of calendar_service.py, all of academic_structure_service.py) writes no audit record. The reviewer correctly notes confirm_promotion already threads an actor and generates an operation_id - the natural audit anchor already exists in that function and simply isn't used for a generic AuditLog row (though its StudentPlacementHistory write substitutes adequately for FR-ADM-006's promotion path specifically, per my own analysis above).
- **Non-blocking suggestions from the reviewer** (independently spot-checked, agree with all): students.py:22-26 validates the 25MB upload limit but not MIME/content-type server-side, contrary to backend.md's stated rule; students.py:25 raises ValueError directly in the route rather than via the service-layer error types used everywhere else (harmless - main.py maps it to 400 - but inconsistent style); no formal doc exists yet distinguishing which admin actions require audit_logs rows vs. which don't, which is arguably the root cause of the repo-wide gap above.

## Overall Verdict

**BLOCKED**

## Blocking Issues

1. **FR-ADM-006 Post-condition violated: "allocation is audited."** enrollment_service.auto_enroll_student and enrollment_service.assign_elective (backend/app/services/enrollment_service.py:90-95, 98-168) write zero audit record, and the admin routes that call them (backend/app/api/routes/enrollments.py:60-66 auto_enroll, :69-80 assign_elective) don't even accept/pass current_user, so there is no way to add one without a route-signature change. confirm_promotion (enrollment_service.py:270-335) is adequately audited via StudentPlacementHistory (actor_id + operation_id + effective_date), so only the auto-enrollment and elective-selection paths need a fix. This is a direct, literal SRS Post-condition, not a style preference - treated as blocking per this verification's mandate. Fix: thread current_user/actor through both routes into the service, and write an AuditLog row (action AUTO_ENROLL/ASSIGN_ELECTIVE) in the same transaction, following the exact pattern already used in assignment_service.set_subject_owner (assignment_service.py:110-121).

2. **AC-001's Teacher-Section-scoping scenario is neither implemented nor tested**, despite being explicitly listed as in-scope for this phase (plan.md's own Requirements table quotes AC-001's full Given/When/Then, and its Test Plan table explicitly promises test_auth_api.py::test_role_scope_enforcement covering "Teacher sees only assigned Section's students... Negative: Teacher requests unassigned Section returns 403/404"). No such endpoint or query-scoping logic exists anywhere in backend/app/api or backend/app/services (confirmed via grep -rn "UserRole.TEACHER" backend/app - the only three matches are all inside assignment_service.py's "assignee must have role TEACHER" checks, none of them data-scoping). The delivered test (test_auth_api.py:86-92, test_role_scope_enforcement_teacher_cannot_reach_admin_routes) tests a different scenario (Teacher denied an Admin-only route), not AC-001's literal text. This is a discrepancy between what the human-approved plan.md committed to and what was implemented - requires a human decision: either (a) add a minimal Teacher-facing, Section-scoped read endpoint plus the promised test in this phase, or (b) amend plan.md to explicitly narrow AC-001's Phase-1 scope to the Admin/Student dimensions only, with a documented reason why Teacher-Section data scoping is deferred to a later phase (e.g. Phase 2+, once Teachers have assigned content to view). This call is not mine to make since it changes what plan.md commits to.

Non-blocking findings (do not block this phase, but should be tracked): JWT secret has no production-strength startup validation (config.py:24); useAuth.ts/authSlice.ts duplicates React-Query server state into Redux against .claude/rules/frontend.md; CSV upload endpoint has no server-side MIME/content-type check (students.py:22-26); students.py:25 raises ValueError directly instead of the service-layer error types used elsewhere; no documented policy for which admin actions require audit_logs rows.

## Shipment Record

Not applicable - verdict is BLOCKED. No branch, commit, or PR has been created for this phase.

---

## Re-verification (2026-09-28)

Triggered by the human ("verify it") after `phase-planner-implementer` implemented the
rework approved in `plan.md`'s "Rework Approved After Verification (2026-09-27)"
section (six items). `docs/phase-state.json` showed `status: "implemented"` going in.
This section is a full re-verification (SRS/ADR trace re-run in full, not just the
rework diff), per this agent's own mandate - the original findings above are kept for
history and are not edited.

### Rework items - all six confirmed resolved

| # | Item | Resolution confirmed |
|---|---|---|
| 1 | ADR-0011 audit-every-mutation | `backend/app/services/audit.py` (new shared helper, `db.add()` only, caller commits) is used with zero hand-built `AuditLog(...)` elsewhere. Every mutating function in `academic_structure_service.py`, `subject_service.py`, `assignment_service.py`, `subject_instance_service.py`, `student_import_service.py`, `enrollment_service.py` (`auto_enroll_student` enrollment_service.py:89-107, `assign_elective` enrollment_service.py:110-189, `confirm_promotion` enrollment_service.py:286-362), `calendar_service.py`, and `auth_service.py` now takes `actor: User` and calls `audit.record(...)`/`_record_audit(...)` in the same transaction. Every route (`enrollments.py`, `academic_structure.py`, `subjects.py`, `subject_instances.py`, `students.py`, `calendar.py`, `admin_accounts.py`) passes `current_user` through. Confirmed by direct read of every listed file, not just the previously-named two functions. |
| 2 | Teacher Section-scoped read (AC-001) | `backend/app/services/teacher_service.py` + `backend/app/api/routes/teacher.py`: `GET /teacher/sections/{section_id}/students`, DB-level join `TeacherAssignment`→`SubjectInstance`→`Section` (`_teacher_has_section_access`, teacher_service.py:27-38), 404 with no data on an unassigned Section. `test_auth_api.py::test_role_scope_enforcement` (lines 106-186) covers both the AC-001 positive (Teacher sees only Section A's one Student) and negative (Section B → 403/404, no `roll_number` in body) scenarios exactly as plan.md promised. |
| 3 | ADR-0012 Admin-only reset | No code change; confirmed still true - `auth_service.issue_password_reset` requires `actor.role == ADMIN` (auth_service.py:213-214); no public reset-request route exists in `routes/auth.py`. |
| 4 | JWT secret hardening | `backend/app/core/config.py:51-67` - `model_validator` rejects the placeholder or a secret <32 bytes outside `development`/`test`. `.env.example` updated with matching guidance. `backend/tests/unit/test_config.py` (4 tests) covers placeholder-rejected, short-rejected, strong-accepted, and placeholder-allowed-in-dev. |
| 5 | Redux/`auth/me` duplication removed | `frontend/src/hooks/useAuth.ts` calls `useMe()` (React Query) directly and returns its data; no `authSlice.ts` file exists anywhere in the repo (confirmed via grep, zero hits for `authSlice`/`setUser`); `frontend/src/store/index.ts` has an empty `reducer: {}`, documented as reserved for future client-only state. |
| 6 | CSV content-type/extension check | `student_import_service.py::validate_upload` (lines 57-68) checks `.csv` extension and `ALLOWED_CONTENT_TYPES`, raising `ValidationError` (not a route-level `ValueError`). Tests: `test_student_import_service.py::test_validate_upload_rejects_non_csv_extension`/`test_validate_upload_rejects_unsupported_content_type`/`test_validate_upload_accepts_valid_csv`, plus integration `test_student_import_api.py::test_import_rejects_non_csv_extension`. |

The two original blocking issues (audit-trail gap on `auto_enroll_student`/`assign_elective`; missing AC-001 Teacher-scoping) are both resolved and independently re-verified by reading the code myself, not just trusting `plan.md`'s account.

### Full SRS/ADR re-trace (not limited to the rework)

Re-read every FR-AUTH-*/FR-ADM-*/FR-STU-001/BUS-*/AC-* row from `plan.md`'s Requirements
table against current code. All PASS verdicts from the original table above still hold
and are reconfirmed (no regressions found in `academic_structure_service.py`,
`subject_service.py` incl. ADR-0002 row-lock, `calendar_service.py`, `assignment_service.py`).
ADR-0001 (CSRF) reconfirmed on every mutating router including the new `teacher.py`
(GET-only, correctly has no CSRF dependency - consistent with ADR-0001's "every
state-changing request" scope). ADR-0009 (VARCHAR+CHECK enums) and ADR-0007
(CLASS/LAB slot types) unaffected by the rework, reconfirmed unchanged.

Two **new** findings surfaced only by this round's full re-trace (neither is a
rework-item regression; both existed before this rework and were not caught by the
prior verification pass):

**Finding A - FR-ADM-006 Val ("no ... mismatches") not enforced for promotion/transfer.**
`enrollment_service.preview_promotion` (enrollment_service.py:247-283) and
`confirm_promotion` (enrollment_service.py:286-362) accept `to_batch_id`,
`to_semester_no`, and `to_section_id` as three independent fields
(`schemas/enrollment.py::PromotionRequest`) with **no check that `to_section_id`'s
`Semester` actually belongs to `to_batch_id` with number `to_semester_no`**
(`Section.semester_id` → `Semester.batch_id`/`Semester.number`, confirmed in
`models/academic_structure.py:82-106`). `frontend/src/pages/admin/PromotionTransfer.tsx`
takes the three as independent inputs, not one derived selection, so an Admin
typo (or a direct API caller) produces an internally-inconsistent
`Student.batch_id`/`current_semester_no`/`section_id` triple that `confirm_promotion`
will still commit, audit, and report as success - no capacity conflict is raised
because capacity is checked only against `to_section_id`'s own `capacity`, not
against path consistency. This is exactly the class of error FR-ADM-006's Val
clause ("no duplicates, **mismatches**, capacity overflow, or missing required
elective") is written to prevent, and `test_enrollment_service.py`'s promotion
tests (lines 223-345) only ever exercise already-consistent triples, so the gap
is untested as well as unvalidated. Confirmed by independent reading of
`enrollment_service.py` and the model file, not just the delegated reviewer's claim.

**Finding B - ADR-0011's own test-assertion clause not met.** ADR-0011 states
"Tests assert that the audit row exists for each mutating service function" - this
is unmet for a majority of Phase 1's mutating functions:
- `auth_service.py` - **zero** audit-row tests for any of its 7 mutating functions
  (`create_account`, `deactivate_account`, `issue_invitation`, `issue_password_reset`,
  `consume_invitation`, `consume_password_reset`, `logout`), despite `auth_service`
  being explicitly named in ADR-0011/rework item 1. Confirmed: `grep -i audit
  backend/tests/unit/test_auth_service.py backend/tests/integration/test_auth_api.py`
  returns zero matches.
- `subject_instance_service.py` - **no dedicated test file exists at all**
  (`create_subject_instance`/`activate_subject_instance` are only exercised as setup
  fixtures inside other services' test files); no audit-row assertion for
  `CREATE_SUBJECT_INSTANCE`/`ACTIVATE_SUBJECT_INSTANCE`; two of its own `ValidationError`
  branches (Program/Semester mismatch at subject_instance_service.py:39, duplicate
  instance at subject_instance_service.py:48) are entirely untested.
- `academic_structure_service.py` - only `CREATE_INSTITUTE`'s audit row is asserted
  (`test_academic_structure_service.py:134-136`); `CREATE_DEPARTMENT`/`CREATE_PROGRAM`/
  `CREATE_BATCH`/`CREATE_SEMESTER`/`CREATE_SECTION` have none.
- `calendar_service.py` - only `CREATE_ACADEMIC_CALENDAR`'s audit row is asserted
  (`test_calendar_service.py:245-247`); `SET_EXAM_DATE`/`ADD_TIMETABLE_SLOT` have none.
- `subject_service.py` - only `CREATE_SUBJECT`'s audit row is asserted
  (`test_subject_service.py:276-278`); `CREATE_ELECTIVE_GROUP`/`SET_UNITS` have none.

Per this verification workflow's own instruction ("Read `docs/decisions/README.md`
and check the implementation against every Accepted ADR that affects this phase. An
ADR violation is a blocking finding"), this is treated as blocking rather than a
style note, even though the audit *rows themselves* are written correctly in every
case (verified by code reading) - only the ADR's test-assertion mandate is unmet.

### Regression Test Results (re-run)

- Backend: `backend/.venv/Scripts/python -m pytest --cov=app.services --cov-report=term-missing -q`
  → **102 passed, 0 failed**, 27 warnings (all `InsecureKeyLengthWarning` from the
  intentionally-weak dev/test JWT secret, plus one benign `httpx`/coverage
  deprecation warning). Coverage on `app.services`: **91%** (exceeds the 80%
  NFR-TST-001 bar). Runtime 73.5s.
- Frontend: `npx vitest run` → **3 test files, 10 tests, all passed** (48.6s,
  environment-startup-dominated). `npx tsc -b --noEmit` → zero errors. `npx eslint .`
  → zero errors/warnings.
- No prior "shipped" phases exist yet (Phase 1 is first), so there is nothing to
  regress against; Section 43 dependency is **None** - confirmed N/A.
- All figures above are freshly executed in this session, not carried over from the
  original report.

### Explicitly unverified (environment-limited) - unchanged from original assessment

Docker/Postgres/Redis remain unavailable in this execution environment. The four
items listed in the original report (live-Postgres migration run, ADR-0002 row-lock
under real concurrency, ADR-0009 enum behavior, ADR-0006 live-Redis fixed-window
burst behavior) are unchanged and still assessed **non-blocking** for the same
reasons given there - re-confirmed, not re-argued, in this pass.

### Code Reviewer Findings (delegated to `agent-skills:code-reviewer`, rework diff + quick full pass)

Verdict returned: **REQUEST CHANGES**. Summary of findings (each independently
re-verified by this agent by reading the cited files before being included above
as Finding A/B):

- **Correctness (Important):** Finding A above (promotion/transfer mismatch) -
  the reviewer's one substantive correctness finding, corroborated independently.
- **Correctness/Testing (Important):** Finding B above (ADR-0011 test-assertion
  gap across `auth_service.py`, `subject_instance_service.py`, and partial gaps in
  three other services) - corroborated independently via the same greps shown above.
- **Security:** No new issues. CSRF + role dependencies confirmed present on every
  mutating router including `teacher.py` (correctly absent there, since it is
  GET-only); cookies/bcrypt/generic-error-message/no-secrets-committed all
  reconfirmed; confirmed via `grep -rniE "langchain|langgraph|openai|anthropic|llm"`
  across `backend/app/` and `frontend/src/` that Phase 1 has zero AI/LLM call sites,
  so the NFR-MNT-001/Section 33-34 deterministic-services boundary rule does not
  apply to any code in this phase (there is nothing to violate it).
- **Architecture:** No new issues; the `audit.py` helper's shape (add-but-don't-commit,
  caller owns the transaction) is correct and consistently applied.
- **Readability/Performance:** No issues raised.
- **Non-blocking suggestions (tracked, not required for this phase):**
  `auto_enroll_student`'s audit-only-when-non-empty behavior could use a one-line
  comment; `StudentImport.tsx` has no client-side MIME/size pre-check (server-side
  enforcement is correct and is what matters per NFR-SEC); `config.py`'s hardening
  is contingent on `ENVIRONMENT` being set correctly in every non-dev deployment
  (worth a comment, not a defect); `plan.md`'s file-list line describing
  "safe-deactivate logic" for `academic_structure_service.py` doesn't match the
  code (only `create_*` functions exist - no FR-ADM-001 Val/Post/AC requires
  hierarchy-entity deactivation, so this is a documentation mismatch, not a
  functional gap).

### Overall Verdict (Re-verification)

**BLOCKED**

All six previously-approved rework items are correctly and completely implemented -
this is not a regression of the prior rework. However, this full re-verification
pass surfaced two new findings (Finding A: FR-ADM-006 Val "mismatches" gap in
promotion/transfer; Finding B: ADR-0011's test-assertion clause unmet across
several services) that this workflow's own rules classify as blocking (Val-clause
and ADR-compliance gaps), so the phase cannot ship yet.

### Blocking Issues (Re-verification)

1. **FR-ADM-006 Val ("no ... mismatches") - promotion/transfer accepts an
   internally-inconsistent placement triple.** `backend/app/services/enrollment_service.py:247-283`
   (`preview_promotion`) and `:286-362` (`confirm_promotion`) never verify that
   `to_section_id`'s `Semester.batch_id` equals `to_batch_id` and
   `Semester.number` equals `to_semester_no`. Fix: in `preview_promotion` (the
   shared read-only gate both functions call), look up `to_section_id`'s
   `Semester`/`Batch` and raise `ValidationError` if they disagree with
   `to_batch_id`/`to_semester_no`; add a negative test asserting the mismatch is
   rejected with zero writes.

2. **ADR-0011's test-assertion mandate not met.** `backend/app/services/auth_service.py`
   has zero audit-row tests for 7 mutating functions; `backend/app/services/subject_instance_service.py`
   has no test file at all (zero audit-row tests, two untested validation branches
   at lines 39 and 48); `academic_structure_service.py`, `calendar_service.py`, and
   `subject_service.py` each assert an audit row for only one of their several
   mutating functions. Fix: add `test_*_writes_audit_log` tests (mirroring the
   existing pattern in e.g. `test_subject_service.py:261`) for every remaining
   mutating function in these five files, and add `backend/tests/unit/test_subject_instance_service.py`
   covering both validation branches plus both actions' audit rows.

Non-blocking findings carried forward or newly noted (tracked, not required for
this phase): `auto_enroll_student`'s conditional-audit-on-empty behavior could use
a comment; `StudentImport.tsx` has no client-side upload pre-check; `config.py`'s
JWT hardening depends on `ENVIRONMENT` being set correctly per deployment;
`plan.md`'s "safe-deactivate logic" file-list line doesn't match the delivered
code (documentation-only mismatch).

### Shipment Record (Re-verification)

Not applicable - verdict is BLOCKED. No branch, commit, or PR has been created for
this phase. Per this workflow's Step 6, stopping here; awaiting a further rework
cycle (or a human decision to explicitly waive Finding A and/or Finding B) before
any further verification pass.

---

## Re-verification 2 — targeted (2026-09-28)

**Scope note:** this is a *targeted* re-verification of the "Rework 2 Approved
After Re-verification (2026-09-28)" fix in `plan.md`, not a full re-run of Steps
2-4. Per the instructions for this pass, the full SRS/ADR trace and the delegated
`agent-skills:code-reviewer` review were not re-run, since nothing in checks 1-4
below surfaced anything warranting it. All earlier sections of this report are
unedited.

### Check 1 — Change scope confirmed by direct file read

No prior committed version of `backend/` exists to `git diff` against (the whole
`backend/` tree is untracked per `git status`), so scope was confirmed by reading
the current files in full and comparing them against the prior verification
pass's own line-by-line description of the pre-fix code (Finding A/B text above),
rather than by diffing.

- **Filesystem mtime scan** (`find backend -newer verification-report.md`,
  excluding `.venv`/`__pycache__`) returned exactly seven files, matching the
  human's declared list with no extras: `backend/app/services/enrollment_service.py`
  and six test files (`test_enrollment_service.py`, `test_auth_service.py`,
  `test_academic_structure_service.py`, `test_calendar_service.py`,
  `test_subject_service.py`, new `test_subject_instance_service.py`). No other
  file under `backend/` or `frontend/` is newer than the report. `docs/phases/phase-1-foundation/plan.md`,
  `docs/phase-state.json`, and `CLAUDE.md` are also newer, matching the declared
  non-code changes.
- **`enrollment_service.py`**: full read confirms the only behavioural change is
  in `preview_promotion` (lines 261-269) - a `Semester` lookup on `to_section_id`
  plus a `ValidationError` if `semester.batch_id != to_batch_id or semester.number
  != to_semester_no`, exactly the fix `plan.md`'s Rework 2 item 1 specifies.
  `confirm_promotion` calls `preview_promotion` first (line 309), so it inherits
  the guard unchanged - no separate check was added or needed there.
  `auto_enroll_student`, `assign_elective`, `get_active_enrollments`,
  `required_electives_missing`, and the rest of `confirm_promotion`'s body are
  byte-for-byte consistent with how the prior verification pass described them
  (audit-on-non-empty in `auto_enroll_student`, `ConflictError` on capacity in
  `assign_elective`, `StudentPlacementHistory` write in `confirm_promotion`) -
  no incidental behavioural change found.
- **Test-file changes**: `test_enrollment_service.py`'s `_promotion_target`
  helper (lines 152-166) now explicitly builds the target `Semester` under
  `ctx["batch"].id` (docstring: "consistent with `to_batch_id`/`to_semester_no`")
  - this is the "corrected pre-existing test data" the human described. Read
  every call site of `_promotion_target` in the file: all pre-existing positive
  tests (`test_promotion_preview_no_mutation`, `test_promotion_confirm_atomic_with_history`,
  `test_confirm_promotion_blocked_on_capacity_conflict`, `test_promotion_unknown_student_not_found`)
  pass `to_batch_id=ctx["batch"].id`/`to_semester_no=target_semester.number` -
  i.e. now-consistent triples - with their original assertions (row counts,
  history fields, exception types) unchanged and unweakened. Four new negative
  tests were added (`test_preview_promotion_wrong_batch_rejected`,
  `test_preview_promotion_wrong_semester_number_rejected`,
  `test_confirm_promotion_wrong_batch_rejected`,
  `test_confirm_promotion_wrong_semester_number_rejected`), each asserting
  `ValidationError` and a `_counts()` helper (Enrollment + StudentPlacementHistory
  + AuditLog rows, `test_enrollment_service.py:169-177`) unchanged before/after -
  i.e. genuinely zero writes across all three tables, not just the Enrollment
  table. The other five test files gained only new `test_*_writes_audit_log`
  (and, for `subject_instance_service`, two new validation-branch tests) - no
  existing assertion in any of them was found to be removed or loosened.

### Check 2 — Finding A (FR-ADM-006 Val "mismatches") resolved

Confirmed resolved for both the positive and negative direction, for both
`preview_promotion` and `confirm_promotion`:

- Positive: `test_promotion_preview_no_mutation` and
  `test_promotion_confirm_atomic_with_history` still pass with a consistent
  triple (unchanged behaviour for the valid case).
- Negative (wrong batch): `test_preview_promotion_wrong_batch_rejected` and
  `test_confirm_promotion_wrong_batch_rejected` assert `ValidationError` and
  zero rows written (Enrollment/StudentPlacementHistory/AuditLog counts
  unchanged, `Student.section_id`/`batch_id` unchanged after `db_session.refresh`).
- Negative (wrong semester number): `test_preview_promotion_wrong_semester_number_rejected`
  and `test_confirm_promotion_wrong_semester_number_rejected` - same assertions,
  using `target_semester.number + 1` as the mismatched input.
- Code path confirmed by direct read: `enrollment_service.py:257-269`.

### Check 3 — Finding B (ADR-0011 test-assertion clause) resolved

Cross-referenced every mutating function found by `grep -n "^def \|audit.record\|_record_audit"`
in each of the five files against the corresponding test file's
`test_*_writes_audit_log` functions. All are now covered - none missing:

| Service | Mutating functions | Audit-row test present |
|---|---|---|
| `auth_service.py` | `create_account`, `deactivate_account`, `issue_invitation`, `issue_password_reset`, `consume_invitation`, `consume_password_reset`, `logout` | All 7 - `test_auth_service.py:246-317` |
| `subject_instance_service.py` | `create_subject_instance`, `activate_subject_instance` | Both - `test_subject_instance_service.py:83-94`, `:161-191`; plus new `test_create_subject_instance_program_semester_mismatch_rejected` and `test_create_subject_instance_duplicate_rejected` covering the two previously-untested validation branches |
| `academic_structure_service.py` | `create_institute`, `create_department`, `create_program`, `create_batch`, `create_semester`, `create_section` | All 6 - `test_academic_structure_service.py:130-226` |
| `calendar_service.py` | `create_academic_calendar`, `set_exam_date`, `add_timetable_slot` | All 3 - `test_calendar_service.py:232-319` |
| `subject_service.py` | `create_elective_group`, `create_subject`, `set_units` | All 3 - `test_subject_service.py:261-325` |

No mutating function in any of the five files is still missing an audit-row
test. `enrollment_service.py`'s three mutating functions
(`auto_enroll_student`/`assign_elective`/`confirm_promotion`) were already
covered before this rework and remain covered.

### Check 4 — Regression run (full backend suite)

`backend/.venv/Scripts/python -m pytest --cov=app.services --cov-report=term-missing -q`
→ **130 passed, 0 failed**, 27 warnings (same `InsecureKeyLengthWarning`/`httpx`
warnings as before, no new warning classes). Coverage on `app.services`: **92%**
(up from 91%, still exceeds the 80% NFR-TST-001 bar). Runtime ~82s. The +28 test
delta versus the prior pass's 102 (4 new promotion-mismatch tests + 7 auth
audit-row tests + 5 academic-structure audit-row tests + 2 calendar audit-row
tests + 2 subject audit-row tests + 8 new subject-instance-service tests =
28) is fully accounted for by the declared file list, with no unexplained
addition or removal.

**Frontend**: filesystem scan (`find frontend -newer verification-report.md`,
excluding `node_modules`/`dist`) returned zero files - frontend was not touched
since the prior report, confirming the human's statement. `npx vitest run` was
therefore not re-run, per this pass's explicit scope.

**Section 43 dependency**: Phase 1's declared dependency remains **None** -
unaffected by this change, still N/A.

### Not re-run in this targeted pass

- Full SRS/ADR trace (Section 2/3 of the standard workflow) - not re-run;
  Rework 2 touches only FR-ADM-006 and ADR-0011, both directly covered by
  Checks 2-3 above, and no other requirement's code changed (Check 1).
- Delegated `agent-skills:code-reviewer` five-axis review - not re-invoked for
  this targeted pass; the change is a small, self-contained validation
  addition plus test-only additions, already read in full above.
- The four previously-noted environment-limited items (live-Postgres
  migration run, ADR-0002 row-lock under real concurrency, ADR-0009 enum
  behavior across dialects, ADR-0006 live-Redis fixed-window burst behavior)
  remain unverified in this environment for the same reasons given in the
  original report - unchanged, non-blocking, restated here for completeness.
- The five non-blocking findings carried in the prior "Re-verification
  (2026-09-28)" section (JWT-hardening-depends-on-`ENVIRONMENT` comment,
  `StudentImport.tsx` client-side pre-check, `auto_enroll_student` comment
  suggestion, `plan.md`'s stale "safe-deactivate logic" file-list line) are
  untouched by this rework and remain open, non-blocking, tracked items for a
  future phase.

### Overall Verdict (Re-verification 2)

**PASS**

Both previously-blocking findings (Finding A: FR-ADM-006 Val "mismatches" gap;
Finding B: ADR-0011 test-assertion gap) are resolved, verified independently by
direct code/test reading rather than by trusting `plan.md`'s account. The change
is scoped exactly to what `plan.md`'s Rework 2 section approved - no other
file, function, or assertion was altered. The full backend regression suite
passes at 130/130 with coverage still above the NFR-TST-001 bar, and no
frontend file was touched.

### Shipment Record (Re-verification 2)

Not applicable yet - verdict is PASS but shipment requires a fresh, explicit
go-ahead in this same conversation per this workflow's Step 6. No branch,
commit, or PR has been created.
