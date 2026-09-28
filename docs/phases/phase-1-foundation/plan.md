# Phase 1 — Foundation — Implementation Plan

## Phase

- Phase number: 1
- Phase name: Foundation
- SRS Section-43 row (quoted verbatim):
  - **Main Features:** Data model, Alembic, invitation/reset/revocable JWT/RBAC, hierarchy, Program-scoped Subjects, Subject Owners, exact exams/timetable, CSV import, capacity-aware electives, promotion/transfer, seed
  - **Requirements:** FR-AUTH-001..004, FR-ADM-001..007, FR-STU-001
  - **Dependencies:** None
  - **Expected Demo:** Validate three roles, revocation, one Subject Owner per Subject, assigned Teacher per instance, read-only enrollment, one elective/group, and previewed transfer with history.

## Requirements in Scope

### Functional Requirements (full fields, pulled via `srs-lookup`)

| ID | Summary |
|---|---|
| FR-AUTH-001 | **Secure Login and Revocation.** Pre: account exists/active. Trigger: login/logout/deactivation/protected request. Input: username/email, password, account state, token version. Processing: verify bcrypt hash; issue a 4-hour JWT with identity, exactly one role, token-version claim, no refresh token; validate account/token version on every protected request; increment token version on logout/deactivation. Val: invalid/inactive credentials and revoked/expired tokens rejected without disclosing credential details. Output: role-appropriate session or authorization error. Post: logout/deactivation invalidates issued access immediately. AC: AC-001. |
| FR-AUTH-002 | **Role and Scope Enforcement.** Pre: authenticated request. Trigger: any protected operation. Input: token, requested action, resource scope. Processing: resolve role and authorized records before the business action executes. Val: Students=self; Teachers=assigned SubjectInstances/sections; Admin=institution scope. Output: authorized result or `403`. Post: no unauthorized data read/changed. AC: AC-001. |
| FR-AUTH-003 | **Account Administration.** Pre: Admin authenticated. Trigger: account maintenance action. Input: identity, role, department/section references, active state. Processing: validate unique identity/references; hash initial/reset password. Val: role/scope assignment must be valid; exactly one role per account (`ADMIN`/`TEACHER`/`STUDENT`). Output: account record. Post: audit record created. AC: a deactivated account cannot log in. |
| FR-AUTH-004 | **Invitation, Reset, and Login Throttling.** Pre: Admin creates/selects the account. Trigger: Admin token generation, user token consumption, or repeated auth failure. Input: account identity, single-use token. Processing: store only token hashes; enforce expiry/use-once; invalidate earlier reset tokens; apply account/IP-aware throttling. Val: public responses never reveal whether an identity exists; email/SMS delivery not required (out-of-band URL delivery by Admin). Output: one-time URL to Admin, activation/reset result to user, or generic failure. Post: password reset increments `token_version`; security actions audited without logging token secrets. AC: used/expired/replaced tokens fail and throttling does not expose credentials. |
| FR-ADM-001 | **Academic Hierarchy.** Pre: Admin authenticated. Trigger: setup action. Input: codes, names, duration, years, semester number/dates, section capacity. Processing: persist Institute→Department→Program→Batch→Semester→Section parent-child relationships. Val: required fields, unique codes within parent, valid year/date ranges, positive capacity. Output: updated hierarchy. Post: records available for allocation. AC: a Section cannot be created without a valid semester/batch path. |
| FR-ADM-002 | **Teacher and Subject Owner Assignment.** Pre: Teacher accounts, Subject, SubjectInstances exist. Trigger: Admin assignment. Input: Teacher, Subject/SubjectInstance, assignment role (`PRIMARY`/`CO`), owner flag. Processing: create/update scoped assignments. Val: account role is `TEACHER`; every active SubjectInstance has a Teacher; exactly one owner per active Subject offering; owner is PRIMARY on at least one related instance. Output: TeacherAssignment and SubjectOwnerAssignment records. Post: operational/approval permissions update. AC: AC-001, AC-002. |
| FR-ADM-003 | **Subject Catalogue.** Pre: Program/semester structure exists. Trigger: Subject maintenance. Input: Subject and Unit attributes (code, name, credits, type, elective group, Unit weightage). Processing: create/update catalogue and Units. Val: unique code in Program/Semester scope; supported type; nonnegative credits; Unit weights each `0..100` and total exactly `100`; elective membership matches type. Output: Subject record. Post: Subject can be instantiated for a Section in the same Program/Semester. AC: invalid scope, duplicate code, or invalid weights are rejected. |
| FR-ADM-004 | **Subject-Section and Teacher Allocation.** Pre: Subject, Section, Teacher exist. Trigger: Admin maps offering. Input: Subject ID, Section ID, Teacher IDs/roles. Processing: create DRAFT SubjectInstance and TeacherAssignments. Val: Subject Program/Semester matches Section path; no duplicate instance; at least one assigned Teacher before activation. Output: SubjectInstance and TeacherAssignment records. Post: content setup can begin. AC: AC-002 (includes successful appearance in affected Student lists after enrollment). |
| FR-ADM-005 | **Student CSV Import.** Pre: department, batch, semester, section exist. Trigger: Admin uploads CSV. Input: roll number, identity/account fields, department, batch, current semester, section. Processing: validate rows, avoid duplicates, create/update allowed student records. Val: required columns, unique roll number, valid references and section capacity. Output: import summary + error file/list. Post: valid Students exist; invalid rows do not create partial records. AC: a mixed file imports valid rows and names invalid row reasons. |
| FR-ADM-006 | **Enrollment, Electives, and Promotion.** Pre: active offerings and Student placement exist. Trigger: import, elective allocation, promotion/transfer, or enrollment refresh. Input: placement, capacities, Admin elective assignment. Processing: auto-enroll from Program+Semester+Section; assign exactly one eligible Subject per required elective group within capacity; preview the authoritative set, validate capacity, confirm atomically, close prior active enrollments where needed, create idempotent `auto_allocated=true` enrollments; support previewed bulk promotion/Section transfer without erasing history. Val: no duplicates, mismatches, capacity overflow, or missing required elective. Output: read-only current Subject list + preserved history. Post: allocation is audited. AC: AC-002. |
| FR-ADM-007 | **Academic Calendar, Exams, and Timetable.** Pre: semester, Sections, SubjectInstances exist. Trigger: calendar/timetable maintenance. Input: dates, windows, exact exams, recurring start/end slots. Processing: store normalized timezone-aware constraints (institution timezone, term dates, holidays, IA/practical/university windows, exact SubjectInstance exam dates, recurring Section class/lab slots). Val: start precedes end; dates lie in term; exact exams lie in their applicable window; overlapping mandatory events rejected. Output: complete planning calendar/timetable. Post: Planner (future phase) can compute deadlines/free blocks without double counting. AC: AC-003. |
| FR-STU-001 | **Read-Only Assigned Subjects.** Pre: Student authenticated, enrollments exist. Trigger: Student opens subjects. Input: Student identity. Processing: query own authoritative enrollments. Val: no mutation endpoint permitted. Output: Subject list. Post: none. AC: AC-002. |

### Business Rules (Section 11, modules M01–M04 touched by this phase)

| ID | Rule | Why in scope |
|---|---|---|
| BUS-001 | Students must never manually select, add, or drop subjects. | FR-STU-001 must expose zero mutation endpoints; enforced via RBAC (FR-AUTH-002) returning `403`. |
| BUS-002 | Enrollment is auto-derived from Program+Semester+Section; Admin assigns exactly one eligible Subject per required elective group within capacity. | Directly governs FR-ADM-006's allocation service and `Enrollment.auto_allocated=true`. |
| BUS-043 | System supports exactly `ADMIN`/`TEACHER`/`STUDENT`; Admin designates one PRIMARY Teacher as Subject Owner; every other assigned Teacher (PRIMARY or CO) has full assigned-instance operations except final shared-artifact activation. | Governs FR-AUTH-003 role enum and FR-ADM-002 ownership constraint. |
| BUS-049 | Admin bulk promotion/Section transfer preserves historical enrollments and previews the new authoritative set before confirmation. | Directly governs FR-ADM-006's promotion/transfer preview-confirm flow. |
| BUS-042 | Lab subjects are excluded from adaptive planning; support only setup, content, coverage, attendance, and reports. | Subject `type` field (FR-ADM-003) must model `LAB` as a distinct type now, even though planner exclusion itself is enforced in Phase 7/12. Noted so the enum is not designed narrowly. |

Modules touched: M01 (Authentication & User Management), M02 (Institution & Academic Setup), M03 (Subject & Student Allocation), M04 (Academic Calendar & Timetable) — per Section 8.

### Acceptance Criteria (Section 40, traced via Section 41's matrix rows BR-001, BR-002, BR-017, plus FR-ADM-002's own AC references)

| ID | Positive / Negative scenario |
|---|---|
| AC-001 | RBAC/scope — GIVEN a Teacher assigned to Section A WHEN requesting its Students THEN only Section A records return. NEGATIVE: GIVEN the same Teacher requests Section B WHEN unassigned THEN `403/404` returns with no data. |
| AC-002 | Auto-enrollment — GIVEN a CSE Semester 3 Section A Student and mapped offerings WHEN allocation runs THEN all applicable and Admin-assigned elective enrollments are created once. NEGATIVE: GIVEN Student credentials WHEN enrollment mutation is requested THEN `403`; no row changes. |
| AC-003 | Calendar/timetable — GIVEN a valid term, institution timezone, exact SubjectInstance exam dates, and recurring Section class/lab timetable WHEN Admin saves THEN Planner (future) reads normalized constraints. NEGATIVE: GIVEN invalid date/time, missing exam deadline, or overlapping timetable rows WHEN saved THEN validation identifies each issue. |
| AC-029 | Security/session — GIVEN a valid invitation/login WHEN used THEN setup and a 4-hour JWT work over TLS; GIVEN reset/deactivation/Admin revocation THEN the prior token version is rejected immediately. NEGATIVE: GIVEN expired/replayed setup/reset token, excessive attempts, secret in repository, or cross-scope ID WHEN tested THEN it is blocked/rate-limited and no protected data leaks. |
| AC-030 | Enrollment change — GIVEN a promotion/transfer WHEN previewed THEN changes/capacity conflicts appear without mutation; WHEN confirmed THEN placement changes atomically with history. NEGATIVE: GIVEN an elective group with zero/multiple selections or exceeded capacity WHEN confirmed THEN operation is blocked. |

Traceability rows consulted (Section 41): BR-001 (FR-ADM-001, FR-ADM-007 → AC-003), BR-002 (FR-ADM-003..006, FR-STU-001 → AC-002, AC-030), BR-017 (FR-AUTH-001..004, FR-TCH-001, FR-NOT-001 → AC-001, AC-029 — only the FR-AUTH-* portion is in this phase's scope; FR-TCH-001/FR-NOT-001 belong to later phases and are explicitly excluded here).

### Section 5 fixed stack (pulled once for this run)

React 18, TypeScript, Tailwind, Redux Toolkit, React Query, Recharts, FastAPI, Python 3.11, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 15 with pgvector, Redis, MinIO, Celery, LangGraph/LangChain, JWT, bcrypt, Docker, Docker Compose. Phase 1 has no AI/RAG/deterministic-service surface, so pgvector, Redis, MinIO, Celery, and LangGraph/LangChain are provisioned in `docker-compose.yml` for forward-compatibility with later phases but are not exercised by Phase 1 application code beyond container wiring.

### Relevant NFR-SEC IDs (Section 36) governing implementation, not just design intent

NFR-SEC-004 (4h JWT, no refresh, `token_version` revocation), NFR-SEC-005 (bcrypt only, never log plaintext), NFR-SEC-006/007/008 (query-level role/ownership scoping, Student enrollment mutation denial), NFR-SEC-011 (no secrets/PII in logs), NFR-SEC-012 (audit on approvals/overrides/security actions), NFR-SEC-013 (env-based secrets, no secrets in source control), NFR-SEC-015 (single-use expiring invitation/reset tokens, revoke JWTs after reset), NFR-SEC-016 (rate limiting on login/invitation/reset with non-enumerating errors).

## Dependencies Check

Section 43 lists Phase 1's dependency as **None**. Confirmed:

| Dependency | Satisfied? | Evidence |
|---|---|---|
| None (Phase 1 is the first phase) | N/A | No prior phase deliverables required. |

### Repo-state vs. `phase-state.json` reconciliation (required by Step 3)

`phase-status` skill (`.claude/skills/phase-status/check.py`) reported:

```
1  Foundation  not_started  True   <-- NOTE: deliverables found but state file says not yet done
7  Planner     not_started  True   <-- NOTE: deliverables found but state file says not yet done
```

**Investigated and this is a false positive of the heuristic, not real progress.** The script's hint words for Phase 1 (`backend`, `alembic`, `migrations`) and Phase 7 (`planner`, `study_plan`) match plain-English mentions of those words inside this repo's *own process/tooling files* — agent definitions and mirrored rule copies under `.agents/` and `.github/` (e.g. `.agents/rules/backend.md`, `.github/instructions/backend.instructions.md`, `.agents/agents/phase-planner-implementer/agent.md`). The heuristic's exclusion list only skips `.claude/`, not `.agents/` or `.github/`, which are exact/near-exact mirrors of `.claude/`'s own agent-definition prose (per recent commits "Skill added for live testing in both .claude and .agents" and "Copilot Setup") and use the same vocabulary. A direct filesystem check confirms:

```
backend/   → does not exist
frontend/  → does not exist
docs/      → only phase-state.json, phases/ (empty), templates/
```

No `backend/`, `frontend/`, migrations, or any application code exist anywhere in the repo. `docs/phase-state.json` correctly shows Phase 1 as `not_started`. Proceeding on that basis. (Flagging this now so a future invocation of `phase-status` doesn't get mis-read as meaning Phase 1 already has partial code — it does not; the tool needs its exclusion list extended to `.agents/` and `.github/` at some point, but that is a tooling fix outside this plan's scope and is called out under Risks & Open Questions below.)

## Files to Create

### Repository scaffolding

| Path | Purpose |
|---|---|
| `docker-compose.yml` | Orchestrate `backend`, `frontend`, `postgres` (pgvector image), `redis`, `minio`, and a `celery` worker service for forward compatibility; Phase 1 only truly exercises `backend`/`postgres`. |
| `.env.example` | Documented required environment variables (DB URL, JWT secret, bcrypt rounds, MinIO/Redis creds placeholders, cookie `Secure` flag, allowed CORS origin, per-account/per-IP rate-limit counts and window lengths per ADR-0006) — no real secrets. |
| `.gitignore` additions | Ensure `.env`, `__pycache__/`, `node_modules/`, `.venv/` etc. are ignored (check existing `.gitignore` first; extend, don't duplicate). |

### Backend (`backend/`)

| Path | Purpose |
|---|---|
| `backend/pyproject.toml` | Ruff/mypy/pytest config, dependency pins matching Section 5 stack (FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, psycopg, passlib[bcrypt], PyJWT (ADR-0010), python-multipart, uvicorn). |
| `backend/app/__init__.py`, `backend/app/main.py` | FastAPI app factory, router registration, exception handlers (no credential-detail leakage). |
| `backend/app/core/config.py` | Pydantic Settings loading from environment (`.env` via `python-dotenv` in dev only). |
| `backend/app/core/security.py` | bcrypt hashing helpers, JWT encode/decode (4h expiry, `token_version` claim, single role claim), httpOnly auth-cookie set/clear and double-submit CSRF check (ADR-0001). |
| `backend/app/core/rate_limit.py` | Single shared Redis fixed-window rate-limit helper, limits from settings (ADR-0006). |
| `backend/app/core/deps.py` | FastAPI dependencies: `get_current_user`, `require_role(*roles)`, DB session dependency. |
| `backend/app/db/base.py`, `backend/app/db/session.py` | SQLAlchemy 2.0 declarative base, engine/session factory. |
| `backend/app/models/user.py` | `User` model: id, login identity, password hash, role enum, `is_active`, `token_version`, invited/reset timestamps. |
| `backend/app/models/academic_structure.py` | `Institute`, `Department`, `Program`, `Batch`, `Semester`, `Section` models with FK hierarchy and unique-code-within-parent constraints. |
| `backend/app/models/calendar.py` | `AcademicCalendar`, `SectionTimetableSlot` models. |
| `backend/app/models/subject.py` | `Subject`, `ElectiveGroup`, `Unit` models (Unit weightage rows, `0..100`, per-row DB check; sum-to-100 enforced in `subject_service` under a Subject row lock — ADR-0002). |
| `backend/app/models/subject_instance.py` | `SubjectInstance`, `TeacherAssignment`, `SubjectOwnerAssignment` models. |
| `backend/app/models/student.py` | `Student` model (roll number, dept/batch/section FKs, current semester). |
| `backend/app/models/enrollment.py` | `Enrollment`, `StudentPlacementHistory` models (`auto_allocated=true` default, effective dates, status). |
| `backend/app/models/auth_tokens.py` | `InvitationToken`, `PasswordResetToken` models storing only token *hashes*, expiry, used flag. |
| `backend/app/models/audit_log.py` | `AuditLog` model (actor, action, entity, before/after, reason, timestamp) — used by every mutating endpoint in this phase. |
| `backend/app/schemas/auth.py` | Pydantic request/response schemas: login, token, invitation-consume, reset-request/consume. |
| `backend/app/schemas/academic_structure.py`, `subject.py`, `enrollment.py`, `calendar.py` | Request/response schemas per FR (no raw dicts, per `.claude/rules/backend.md`). |
| `backend/app/services/auth_service.py` | Login, token issuance/validation, invitation/reset issuance+consumption, throttling (FR-AUTH-001/002/004). Not one of the five "deterministic services" named in the SRS, but still pure/testable business logic separated from the route layer. |
| `backend/app/services/academic_structure_service.py` | Hierarchy CRUD + safe-deactivate logic (FR-ADM-001). |
| `backend/app/services/subject_service.py` | Subject/Unit catalogue CRUD + weight validation (FR-ADM-003). |
| `backend/app/services/assignment_service.py` | Teacher/Subject Owner assignment invariants (FR-ADM-002). |
| `backend/app/services/subject_instance_service.py` | SubjectInstance mapping + activation gate (FR-ADM-004). |
| `backend/app/services/student_import_service.py` | CSV parse/validate/import with row-level reporting (FR-ADM-005). |
| `backend/app/services/enrollment_service.py` | Auto-enrollment, elective allocation, promotion/transfer preview+confirm (FR-ADM-006). |
| `backend/app/services/calendar_service.py` | Calendar/timetable CRUD + overlap/window validation (FR-ADM-007). |
| `backend/app/api/routes/auth.py` | `/auth/login`, `/auth/logout`, `/auth/invitations`, `/auth/password-reset*`. |
| `backend/app/api/routes/admin_accounts.py` | Admin account CRUD/activate/deactivate (FR-AUTH-003). |
| `backend/app/api/routes/academic_structure.py` | Institute/Department/Program/Batch/Semester/Section endpoints. |
| `backend/app/api/routes/subjects.py` | Subject/Unit/ElectiveGroup endpoints. |
| `backend/app/api/routes/subject_instances.py` | SubjectInstance + TeacherAssignment/SubjectOwnerAssignment endpoints. |
| `backend/app/api/routes/students.py` | Student CSV import endpoint + admin student CRUD. |
| `backend/app/api/routes/enrollments.py` | Read-only Student enrollment list (FR-STU-001), Admin allocation/promotion/transfer preview+confirm endpoints (FR-ADM-006). No Student-facing mutation route exists at all (BUS-001). |
| `backend/app/api/routes/calendar.py` | Academic calendar/timetable endpoints. |
| `backend/alembic/env.py`, `backend/alembic.ini` | Alembic wiring against `app.db.base.Base.metadata`. |
| `backend/alembic/versions/0001_initial_foundation_schema.py` | Single initial migration for all Phase 1 tables (see Migrations section). |
| `backend/scripts/seed_demo_data.py` | Seeds one Institute → one Department → one Program → one Batch → two Sections, a handful of Subjects (including one elective group and one LAB-type Subject), Teacher/Student accounts, and calendar/timetable rows, per Section 5/43's "seed" deliverable. |
| `backend/tests/unit/test_auth_service.py` | Login success/failure, token issuance/expiry, revocation-on-logout/deactivation, invitation/reset issuance+consumption incl. expired/reused/replaced tokens, throttling. |
| `backend/tests/unit/test_academic_structure_service.py` | Hierarchy validation (unique codes, date ranges, positive capacity, section-without-valid-path rejection). |
| `backend/tests/unit/test_subject_service.py` | Unit weight sum-to-100, duplicate code, elective/type mismatch. |
| `backend/tests/unit/test_assignment_service.py` | Exactly-one-owner invariant, non-Teacher-role rejection, every-active-instance-has-a-teacher check. |
| `backend/tests/unit/test_enrollment_service.py` | Auto-enrollment idempotency, elective single-selection, capacity overflow rejection, promotion/transfer preview vs. confirm, history preservation. |
| `backend/tests/unit/test_calendar_service.py` | Overlap detection, exam-date-in-window validation, start-before-end. |
| `backend/tests/integration/test_auth_api.py` | End-to-end login/RBAC/`403` scope tests mapped to AC-001, AC-029. |
| `backend/tests/integration/test_enrollment_api.py` | Read-only enrollment (`FR-STU-001`), Student mutation `403` (AC-002 negative), promotion/transfer preview-confirm API (AC-030). |
| `backend/tests/integration/test_calendar_api.py` | AC-003 positive/negative. |
| `backend/tests/integration/test_student_import_api.py` | Mixed valid/invalid CSV import outcome. |

### Frontend (`frontend/`)

| Path | Purpose |
|---|---|
| `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json` | Scaffolding: React 18 + TypeScript + Vite, Tailwind, Redux Toolkit, React Query. |
| `frontend/src/api/authApi.ts`, `academicStructureApi.ts`, `subjectApi.ts`, `enrollmentApi.ts`, `calendarApi.ts` | React Query hooks wrapping backend endpoints above. |
| `frontend/src/store/authSlice.ts` | Client-only auth/session UI state (current user, role; never the JWT, which lives only in the httpOnly cookie — ADR-0001) — server state (profile data) stays in React Query, not duplicated into Redux, per `.claude/rules/frontend.md`. |
| `frontend/src/pages/Login.tsx` | Login page. |
| `frontend/src/pages/admin/*` (HierarchyManager, SubjectCatalogue, TeacherAssignment, StudentImport, CalendarTimetable, PromotionTransfer) | Admin screens covering FR-ADM-001..007. |
| `frontend/src/pages/student/MySubjects.tsx` | Read-only enrolled-subjects view (FR-STU-001) — no add/drop control anywhere in this component tree. |
| `frontend/src/hooks/useAuth.ts` | Session/role hook. |
| `frontend/src/types/*.ts` | Shared TS types mirroring backend Pydantic schemas. |
| `frontend/src/**/__tests__/*.test.tsx` | Vitest + RTL: role-gated rendering (Admin sees management screens, Student sees only read-only list, no mutate controls rendered for Student), API-call scoping per role. |

## Files to Change

None — this is the first phase in a greenfield repo; there is no existing application code to modify. (`.gitignore`, if it already contains partial entries, will be extended rather than replaced; verified as an "extend" operation above, not a rewrite.)

## Migrations

One initial Alembic migration, `0001_initial_foundation_schema.py`, creating (per Section 31.1 entities in scope for this phase):

- `users` (role enum `ADMIN|TEACHER|STUDENT`, unique login identity, password hash, `is_active`, `token_version` default 0, invited/reset timestamps).
- `invitation_tokens`, `password_reset_tokens` (token *hash* column only, `expires_at`, `used_at`, FK to `users`).
- `institutes` (name, IANA `timezone`).
- `departments` (FK institute, unique code within institute).
- `programs` (FK department, `duration_semesters`, unique code within department).
- `batches` (FK program, `start_year`, `end_year`).
- `semesters` (FK batch, number, `start_date`, `end_date`, unique (batch, number)).
- `sections` (FK semester, name, capacity > 0, unique (semester, name)).
- `academic_calendars` (FK semester, holidays/working-days JSON or child table, version).
- `section_timetable_slots` (FK section, day-of-week, local start/end time, type `CLASS|LAB` per ADR-0007, effective dates; check `start < end`).
- `elective_groups` (FK program, semester_no, name, required flag).
- `subjects` (FK program, semester_no, code, name, credits >= 0, type enum incl. `LAB`, FK elective_group nullable; unique code within (program, semester_no)).
- `units` (FK subject, order, weightage 0..100; DB check constraint per-row range; sum-to-100 enforced in service layer transaction, documented as such since cross-row SUM constraints aren't portable as a simple CHECK).
- `subject_instances` (FK subject, FK section, exact `exam_at` timestamptz, status enum `DRAFT|ACTIVE`; unique (subject, section)).
- `teacher_assignments` (FK user[role=TEACHER], FK subject_instance, role enum `PRIMARY|CO`; unique (teacher, subject_instance)).
- `subject_owner_assignments` (FK subject, FK user[role=TEACHER]; unique (subject) — exactly one owner per Subject enforced by unique constraint on subject_id alone; owner changes update in place and write an `audit_logs` row in the same transaction — ADR-0003).
- `students` (FK user, roll number unique, FK department/batch/section, current semester).
- `enrollments` (FK student, FK subject_instance, elective_group nullable, effective_from/to, status enum, `auto_allocated` boolean default true; unique (student, subject_instance) for active rows via partial unique index).
- `student_placement_history` (FK student, from/to batch/semester/section, effective_date, actor FK user, preview/operation id).
- `audit_logs` (actor FK user, action, entity type/id, before/after JSON, reason, timestamp).

All FKs `ON DELETE RESTRICT` unless a specific cascade is justified in code review; all timestamp columns `timestamptz`; enums stored as `VARCHAR` + named `CHECK` constraints via SQLAlchemy `Enum(native_enum=False, create_constraint=True)`, not native Postgres `ENUM` types (ADR-0009). `StudentPreference` (Section 31.1) is explicitly **deferred to Phase 7** (Planner) — it is not created in this migration since Phase 1's Section 43 row does not list student availability/preferences among its deliverables, and no Phase 1 FR references it.

## Test Plan

Mapped to Phase 1's Expected Demo bar: *"Validate three roles, revocation, one Subject Owner per Subject, assigned Teacher per instance, read-only enrollment, one elective/group, and previewed transfer with history."*

| Demo bar item | Test(s) | AC / FR mapping |
|---|---|---|
| Three roles enforced | `test_auth_api.py::test_role_scope_enforcement` — Teacher sees only assigned Section's students; Student sees only own data; Admin sees institution scope. Negative: Teacher requests unassigned Section → `403/404`. | AC-001, FR-AUTH-002, NFR-SEC-006/007 |
| Revocation | `test_auth_service.py::test_logout_revokes_token`, `test_deactivation_revokes_token`, `test_password_reset_revokes_token` — token_version increments; old JWT rejected immediately after. Negative: replayed pre-revocation JWT rejected. | AC-029, FR-AUTH-001/004, NFR-SEC-004/015 |
| Invitation/reset flow | `test_auth_service.py::test_invitation_single_use`, `test_reset_token_expiry`, `test_earlier_reset_token_invalidated_by_new_one`. Negative: expired/replayed/already-used token rejected without revealing account existence. | AC-029, FR-AUTH-004, NFR-SEC-015/016 |
| Login throttling | `test_auth_service.py::test_login_throttle_after_repeated_failures` — Nth consecutive failure for same account/IP throttled; error message is generic (non-enumerating). | AC-029, FR-AUTH-004, NFR-SEC-016 |
| One Subject Owner per Subject | `test_assignment_service.py::test_exactly_one_owner_enforced` — second owner assignment attempt rejected. Negative: assigning a non-`TEACHER`-role account as owner rejected. | FR-ADM-002, AC-001/AC-002 |
| Assigned Teacher per instance | `test_assignment_service.py::test_active_instance_requires_teacher` — activating a SubjectInstance with zero TeacherAssignments rejected. | FR-ADM-004, FR-ADM-002 |
| Read-only enrollment | `test_enrollment_api.py::test_student_sees_own_enrollments`, `test_student_enrollment_mutation_forbidden` — no `POST/PUT/DELETE` enrollment route exists for Student role; attempted call returns `403` with zero row changes. | FR-STU-001, AC-002 negative, BUS-001, NFR-SEC-008 |
| One elective per required group | `test_enrollment_service.py::test_single_elective_per_group`, `test_missing_required_elective_rejected`, `test_elective_capacity_overflow_rejected`. | FR-ADM-006, BUS-002 |
| Previewed transfer with history | `test_enrollment_service.py::test_promotion_preview_no_mutation`, `test_promotion_confirm_atomic_with_history` — preview call performs zero writes; confirm call is atomic and preserves `student_placement_history` rows referencing prior enrollments. Negative: confirming a preview with a capacity conflict is blocked. | FR-ADM-006, AC-030, BUS-049 |
| Academic hierarchy / calendar validity | `test_academic_structure_service.py`, `test_calendar_service.py::test_overlap_rejected`, `test_exam_date_outside_window_rejected`. Negative: Section creation without valid semester/batch path rejected; overlapping mandatory timetable rows rejected. | FR-ADM-001, FR-ADM-007, AC-003 |
| CSV import row-level reporting | `test_student_import_api.py::test_mixed_valid_invalid_rows` — valid rows create Students; invalid rows produce named per-row reasons; no partial record for an invalid row. | FR-ADM-005 |
| Seed data / demo | Manual/documented run of `backend/scripts/seed_demo_data.py`, verified by `test_seed_data.py::test_seed_is_idempotent_and_consistent` (re-running seed does not duplicate or corrupt records). | Section 43 "seed" deliverable |
| Frontend role-gated rendering | Vitest/RTL integration tests: Admin sees management screens and mutate controls; Student's `MySubjects` page renders zero add/drop controls; unauthenticated/expired-session redirects to login. | FR-STU-001, BUS-001, NFR-SEC frontend rule |
| Coverage | `pytest --cov=app.services` on `auth_service`, `academic_structure_service`, `subject_service`, `assignment_service`, `enrollment_service`, `calendar_service`, `student_import_service` ≥ 80% including boundary/failure cases, per NFR-TST-001 (these are Phase 1's core business-logic services; the SRS's five *named* "deterministic services" — IngestionService, DiagnosticEngine, AutoGrader, LearnerModelService, StudyPlannerService — don't exist yet, so this phase's 80% bar applies to its own service layer by the same testing philosophy). | NFR-TST-001/002 |

## Exact-Algorithm Call-Outs

Not applicable. Phase 1 does not touch Section 23 (Mastery Score), Section 24 (Engagement Score), or Section 25 (Adaptive Study Planner) — those are Phase 6/7 concerns.

## Decisions Applied

All eight open questions from the first draft were resolved by the human reviewer on 2026-09-27 and recorded as ADRs in `docs/decisions/`. This plan follows them:

| ADR | Decision | Where it lands in this plan |
|---|---|---|
| [ADR-0001](../../decisions/ADR-0001-jwt-in-httponly-cookie.md) | JWT in httpOnly/Secure/SameSite=Strict cookie + double-submit CSRF | `core/security.py`, `core/deps.py`, all mutating routes, frontend API client, `authSlice.ts` |
| [ADR-0002](../../decisions/ADR-0002-unit-weight-sum-service-layer.md) | Unit weight sum-to-100 in service layer under a Subject row lock | `subject_service.py`, `units` per-row CHECK, `test_subject_service.py` |
| [ADR-0003](../../decisions/ADR-0003-single-subject-owner-with-audit.md) | One owner row per Subject; changes audited | `subject_owner_assignments` unique index, `assignment_service.py` |
| [ADR-0004](../../decisions/ADR-0004-student-preference-deferred.md) | StudentPreference deferred to Phase 7 | Not in migration `0001` |
| [ADR-0005](../../decisions/ADR-0005-csv-import-row-level.md) | CSV import row-level atomic (savepoint per row) | `student_import_service.py`, `test_student_import_api.py` |
| [ADR-0006](../../decisions/ADR-0006-redis-fixed-window-rate-limit.md) | Redis fixed-window rate limiting, limits in config | `core/rate_limit.py`, `.env.example`, auth routes |
| [ADR-0007](../../decisions/ADR-0007-timetable-slot-types.md) | Timetable slot types `CLASS`/`LAB` only | `section_timetable_slots.type` |
| [ADR-0008](../../decisions/ADR-0008-phase-status-exclusions.md) | phase-status skips agent-tooling folders | Tooling only; the Dependencies Check false positive above is fixed |
| [ADR-0009](../../decisions/ADR-0009-enums-as-varchar-check.md) | Enums as VARCHAR + CHECK | Every enum column in migration `0001` |
| [ADR-0010](../../decisions/ADR-0010-supporting-libraries-vite-dotenv-pyjwt.md) | Vite, python-dotenv (dev only), PyJWT allowed | `frontend/vite.config.ts`, `core/config.py`, `core/security.py`, `pyproject.toml` |
| [ADR-0011](../../decisions/ADR-0011-audit-every-admin-mutation.md) | Every Admin mutation writes an audit_logs row in the same transaction | All Phase 1 services + a shared audit helper |
| [ADR-0012](../../decisions/ADR-0012-admin-only-password-reset.md) | Password reset issued by Admin only | `auth_service.py`, `routes/admin_accounts.py` (confirms Deviation #3) |

## Risks & Open Questions

Open questions 1–8 from the first draft are resolved (see Decisions Applied). Remaining risks:

1. Any deviation from an Accepted ADR discovered during implementation must stop work and be reported, not worked around.
2. ~~Supporting libraries outside the Section 5 list~~ — resolved by ADR-0010 (Vite, python-dotenv, PyJWT).

## Implementation Deviations (recorded during Step 5)

None of these contradict an Accepted ADR; each is called out here per the
"stop and record, don't silently diverge" rule.

1. **Test database: SQLite in-memory, not PostgreSQL.** Docker, a local
   Postgres server, and a local Redis server are all unavailable in this
   execution environment (confirmed: no `docker`, `psql`, or `redis-cli` on
   PATH). The automated test suite (`backend/tests/**`) therefore runs
   against an in-memory SQLite engine created per-test in
   `backend/tests/conftest.py`, and a small in-memory `FakeRedis` stand-in
   (implementing only the `incr`/`expire` calls `RateLimiter` makes) instead
   of a live Redis instance. Production code is unaffected: `docker-compose.yml`
   and `alembic/versions/0001_initial_foundation_schema.py` target
   PostgreSQL 15 exclusively, `app/db/session.py` builds its engine from
   `DATABASE_URL` with no SQLite-specific branching except one documented
   spot - `subject_service.set_units`'s `SELECT ... FOR UPDATE` row lock
   (ADR-0002) is skipped when the bound dialect is `sqlite` (which has no
   row-level locking at all), and applied exactly as ADR-0002 specifies on
   every other dialect, i.e. always in production. `app/core/rate_limit.py`
   always talks to real Redis via `get_redis_client()`; only tests inject
   the fake.
2. **`bcrypt` used directly, not `passlib[bcrypt]`.** `core/security.py`
   calls the `bcrypt` package directly rather than wrapping it in `passlib`.
   Reasons: (a) `passlib`'s bcrypt backend has a known compatibility break
   with `bcrypt>=4.1` (it reads `bcrypt.__about__.__version__`, removed in
   4.1+), which would either pin an old `bcrypt` or fail at import time; (b)
   `bcrypt` is the literal technology Section 5 names - `passlib` was never
   itself part of the fixed stack or ADR-0010's supporting-library list, so
   dropping it removes a dependency rather than adding one. Behavior
   (bcrypt hashing, configurable rounds via `BCRYPT_ROUNDS`) is unchanged.
3. **FR-AUTH-004 password reset is Admin-issued only, no public
   "forgot password" endpoint.** `auth_service.issue_password_reset` requires
   an Admin `actor` and there is no `/auth/password-reset/request`-by-email
   route. This follows the FR's own text ("Pre: Admin creates/selects the
   account. Trigger: Admin token generation... email/SMS delivery not
   required (out-of-band URL delivery by Admin)") - the earlier public
   self-service route sketched in the file-list line ("Admin
   password-reset*") was replaced with `POST
   /admin/accounts/{user_id}/password-resets` to match this precondition
   exactly, mirroring the invitation-issuance endpoint shape.
4. **Backend tests executed on Python 3.12, not 3.11.** Python 3.11 is not
   installed in this environment (`py -0` lists only 3.12 and 3.14); 3.12 was
   used to create the `backend/.venv` test environment. `pyproject.toml`
   still declares `requires-python = ">=3.11,<3.13"` and Docker/CI/production
   should run 3.11 per Section 5 - this is an environment limitation on
   *where tests were run in this session*, not a change to the pinned
   target version.
5. **ESLint legacy config (`.eslintrc.cjs`), not flat config.**
   `.claude/rules/frontend.md` describes flat config as "recommended... since
   this is greenfield," not mandatory. Legacy config was used for broader
   compatibility with the pinned `eslint@8`/`@typescript-eslint@7`/
   `eslint-plugin-react-hooks@4` versions. Flat config can be adopted in a
   later phase without any test/behavior impact if a human wants it.

## Approval

- [x] Approved by human reviewer
- Date approved: 2026-09-27
- Notes: Approved with ADR-0001..ADR-0010 applied (see Decisions Applied). Vite, python-dotenv and PyJWT allowed per ADR-0010.

## Rework Approved After Verification (2026-09-27)

Verification (`verification-report.md`) returned **BLOCKED**. The human reviewer approved the following rework on 2026-09-27. Implement all items, then return to verification.

1. **Audit every Admin mutation (ADR-0011) — clears blocking finding 1.** Add a shared audit helper. Every mutating service function in `academic_structure_service`, `subject_service`, `assignment_service`, `subject_instance_service`, `student_import_service`, `enrollment_service` (including `auto_enroll_student` and `assign_elective`) and `calendar_service`, plus Admin account actions in `auth_service`, takes the acting user and writes `audit_logs` in the same transaction. Routes pass `current_user`. Add tests asserting the audit row for each.
2. **Teacher Section-scoped student read (AC-001, FR-AUTH-002) — clears blocking finding 2.** Add one read-only endpoint (e.g. `GET /teacher/sections/{section_id}/students`) that returns students only for Sections where the Teacher holds a TeacherAssignment on a SubjectInstance of that Section, with the scope filter applied in the DB query; an unassigned Section returns `403/404` with no data. Add `test_auth_api.py::test_role_scope_enforcement` covering both AC-001 scenarios.
3. **Password reset stays Admin-only (ADR-0012).** No code change; Deviation #3 is confirmed.
4. **JWT secret hardening.** In `core/config.py`, reject startup outside development/test when the JWT secret is the placeholder or shorter than 32 bytes. Update `.env.example` guidance. Add a test.
5. **Remove Redux duplication of server state.** `useAuth`/`authSlice` must not mirror the `/auth/me` result; React Query stays the single source of the current user. Update frontend tests.
6. **CSV upload type check.** Validate content type and extension server-side (`text/csv` / `.csv`) in addition to the size limit, raising the service-layer error type rather than `ValueError` in the route. Add a negative test.

## Rework 2 Approved After Re-verification (2026-09-28)

Re-verification (see "Re-verification (2026-09-28)" in `verification-report.md`) returned **BLOCKED** on two new findings. The human reviewer approved fixing both on 2026-09-28.

1. **Promotion/transfer target consistency (FR-ADM-006 Val: "no ... mismatches").** In `enrollment_service.preview_promotion` (and therefore `confirm_promotion`), reject the request with a validation error unless the target Section's Semester belongs to `to_batch_id` and has number `to_semester_no`. Add negative tests (wrong batch, wrong semester number) for preview and confirm, asserting no rows, history or audit entries are written.
2. **Audit-row test coverage (ADR-0011 test clause).** Add tests asserting the `audit_logs` row (action, actor, entity) for every mutating service function: all mutating functions in `auth_service`; both mutating functions in `subject_instance_service` (new `tests/unit/test_subject_instance_service.py`, also covering its two untested validation branches); and every remaining mutating function in `academic_structure_service`, `calendar_service` and `subject_service`.
