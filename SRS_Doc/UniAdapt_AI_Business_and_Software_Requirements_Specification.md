# UniAdapt AI — Business and Software Requirements Specification

## 1. Document Information

| Field | Value |
|---|---|
| Project Name | UniAdapt AI — Department-wise Agentic Learning Platform for Engineering Colleges |
| Document Name | UniAdapt AI — Business and Software Requirements Specification |
| Version | 0.0 |
| Project Type | Final-Year Engineering Project |
| Status | Finalized Requirements Baseline |
| Prepared By | TBD |
| Date | 13 September 2026 |

### 1.1 Requirement Status Labels

| Label | Meaning |
|---|---|
| Confirmed | Approved and treated as a project requirement. |
| Assumption | Working interpretation pending formal stakeholder confirmation. |
| Recommendation | A practical project target or implementation choice, not a confirmed business requirement. |
| Future Scope | Deliberately excluded from the final-year implementation. |

Unless marked otherwise, requirements in this document are Confirmed.

## 2. Project Overview

UniAdapt AI is a department-wise adaptive learning platform for an engineering college. It connects the college's academic structure, approved course content, actual classroom coverage, diagnostic evidence, and each student's available study time to produce explainable daily and weekly study plans.

The platform serves Admins, Teachers, and Students. Admins set up departments, programs, batches, semesters, sections, subjects, calendars, teachers, and student allocations; monitor institution-wide academic operations; and initiate semester-start prerequisite diagnostics. Assigned Teachers prepare academic content, curriculum, and questions; the designated Subject Owner activates shared artifacts. Teachers also record coverage, moderate grades, and act on interventions. Students consume their assigned learning plan, course material, tutor support, practice, quizzes, feedback, and recommendations.

Adaptive learning is required because students begin a semester with different prerequisite knowledge, retain taught topics differently, and have different time constraints. A fixed plan cannot respond to these differences or to the class's real teaching progress. UniAdapt AI therefore builds a per-topic learner model and schedules eligible work according to mastery, exam relevance, urgency, prerequisite importance, decay risk, and teacher direction.

AI/LLM components are used where language understanding or generation is valuable: extracting curriculum structure, generating and critiquing questions, rubric-based subjective grading, answering course-grounded questions, ranking resources, and drafting interventions. Deterministic code is used where results must be reproducible and auditable: ingestion processing, diagnostic item selection, objective/coding grading, mastery and engagement computation, and study-plan calculation. AI does not replace the defined approval gates or deterministic algorithms.

## 3. Problem Statement

The project addresses the following problems:

1. A common study approach does not account for different student knowledge levels, retention, preferences, or available time.
2. Students can enter a semester with gaps in earlier-semester prerequisite topics that block current learning.
3. Teachers and Admins lack a topic-level view of individual and class weakness linked to graded evidence.
4. Classroom syllabus coverage differs by subject-section; diagnostics and planning must use the last actual Teacher-recorded state.
5. Study scheduling can become misleading when required work exceeds available time unless the shortfall is explicitly reported.
6. Assessment results from diagnostics, quizzes, and practice require one consistent grading path before they update mastery.
7. Generated topic graphs can contain cycles, duplicates, or incorrect relationships and therefore require deterministic validation and teacher approval.
8. AI-generated questions can be ambiguous, duplicated, out of scope, or misleading and therefore require critique, teacher approval, and later item analysis.
9. Knowledge and behavior can be incorrectly mixed. Attendance or plan adherence must not inflate topic mastery or distort planner priority.
10. Students need doubt support grounded in approved material without hallucinated content or answer leakage during active assessments.
11. Teachers need control over AI-generated academic content, low-confidence subjective grades, appeals, and student interventions.

## 4. Project Objectives

| ID | Objective | Purpose | Expected Outcome |
|---|---|---|---|
| OBJ-001 | Model the college's department-wise academic structure. | Establish authoritative subjects and enrollments for each Student. | Admin-controlled subject lists derived from Program + Semester + Section. |
| OBJ-002 | Convert approved source material into a teacher-approved topic and prerequisite model. | Give diagnostics, mastery, and planning a common topic structure. | An ACTIVE subject with stable topic IDs and a valid or fallback ordering. |
| OBJ-003 | Build a controlled, approved question bank. | Support diagnostics, practice, and quizzes with traceable questions. | A READY bank containing validated items across required types and difficulty levels. |
| OBJ-004 | Link actual teaching progress to assessments and planning. | Prevent testing or scheduling untaught material. | Per subject-section coverage states used as operational gates. |
| OBJ-005 | Measure Student knowledge with confidence-aware topic mastery. | Avoid false precision and additive difficulty inflating incorrect work. | Recency-decayed, source- and difficulty-weighted mastery with an evidence confidence value and minimum-evidence display gate. |
| OBJ-006 | Keep learning behavior separate from knowledge. | Avoid attendance and adherence corrupting academic mastery or priority. | A separate Engagement Score used only for dashboards and intervention. |
| OBJ-007 | Generate feasible, explainable adaptive study plans. | Match important eligible work to real availability and calendar constraints. | Daily/weekly plans, spaced revision, reasons per slot, and an explicit deficit when time is insufficient. |
| OBJ-008 | Use AI with human approval and deterministic guardrails. | Gain useful language capabilities without surrendering correctness or teacher control. | Traceable AI outputs, approval gates, fallbacks, moderation, and audit records. |
| OBJ-009 | Provide actionable academic visibility. | Help Students, Teachers, and Admins take appropriate action. | Role-scoped dashboards, interventions, and end-semester reports. |

## 5. Project Scope

### 5.1 In Scope

- One engineering college with Institute -> Department -> Program -> Batch -> Semester -> Section hierarchy.
- Admin-managed Program + Semester subject catalogue, Subject Owner and SubjectInstance Teacher assignments, capacity-aware electives, CSV Student import, bulk semester promotion, and automatic enrollment.
- Academic calendar constraints: institution timezone, term dates, holidays, internal and university exam windows, exact SubjectInstance exam dates, practical exam window, and recurring Section class/lab timetable.
- Shared Subject-level Teacher upload and immutable versioning of syllabus, notes, presentations, previous question papers, recommendation-only reference links, and lab manuals.
- Curriculum extraction, topic/prerequisite graph validation, teacher editing, approval, and flat-unit-order fallback.
- Question generation, AI critique, teacher approval, exposure controls, and post-hoc suspect-item analysis.
- Subject-section Coverage Tracker with `NOT_STARTED`, `IN_PROGRESS`, `COVERED`, and `REVISED` states.
- Admin-triggered Prerequisite and Teacher-triggered Coverage Checkpoint Diagnostics with deterministic adaptive selection.
- Common grading for MCQ, True/False, numerical, coding, and subjective items; moderation and appeal flows.
- Exact Learner Model and Adaptive Study Planner algorithms specified in Sections 23-25.
- Student 30-minute availability, preferences, blackout dates, combined deadline-aware daily/weekly plans, material access, self-practice, Teacher-configured quizzes, and feedback.
- Course-grounded RAG Tutor with citations and assessment lockdown.
- Approved-material recommendations and teacher-first interventions.
- Achievable role dashboards and PDF/Excel end-semester reports.
- In-app notifications, daily academic snapshots, versioned prompts, structured AI outputs, traceability, three-role RBAC, audit logs, and project-level testing.

Implementation baseline: React 18, TypeScript, Tailwind, Redux Toolkit, React Query, Recharts, FastAPI, Python 3.11, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 15 with pgvector, Redis, MinIO, Celery, LangGraph/LangChain, JWT, bcrypt, Docker, and Docker Compose.

### 5.2 Out of Scope

- Student self-selection, add/drop, or manual enrollment in subjects.
- Student editing of official exam dates.
- Assignment creation, submission, grading, or recommendations.
- Additional application roles beyond Admin, Teacher, and Student.
- Crawling or ingesting external HTTPS reference links.
- An unrestricted general-knowledge chatbot.
- LLM-based correctness decisions for objective or coding questions.
- Any posting or contribution of platform grades to official university marks, whether AI-assigned or Teacher-moderated.
- Full university ERP, fee, admissions, payroll, hostel, or library management.
- Full remote proctoring or biometric surveillance.
- Multi-college tenancy and production-scale SaaS operations.
- Native mobile applications.
- Email or SMS notification integration; Admin may securely deliver one-time invitation/reset links out of band.
- Production high availability, disaster-recovery infrastructure, or enterprise SLAs.
- Adaptive self-scheduling, virtual execution, or automated evaluation of laboratory work. Lab subjects support setup, content, coverage, attendance, and reports only.

### 5.3 Future Scope

- Multi-college SaaS with tenant isolation.
- ERP/SIS and attendance-device integrations.
- Student elective preference and allocation workflow if approved by the college.
- Native Android/iOS applications and offline learning.
- Advanced cohort analytics and institutional benchmarking.
- Full proctoring, plagiarism services, and richer coding-language sandboxes.
- Additional coding languages and richer assessment formats.
- Production high availability, disaster recovery, and large-scale deployment.

## 6. System Users / Actors

| Actor | Role | Responsibilities | Main System Actions | Data Accessible |
|---|---|---|---|---|
| Admin | Institution-level operator | Maintain academic structure, accounts, calendar, allocation, operational monitoring, and institutional reporting. | CRUD setup data; assign Teachers; import Students; allocate electives; trigger prerequisite diagnostics; monitor departments and coverage; export reports. | Institution setup and academic data; institution and department rollups; sensitive learner detail only where report scope requires it. |
| Teacher | Subject academic and section operator | Supply academic content, operate assigned SubjectInstances, moderate grades, and handle interventions. A designated Subject Owner gives final approval for shared Subject artifacts. | Upload/version content; edit curriculum/questions; activate shared versions only when designated Subject Owner; update coverage/attendance; create checkpoints/quizzes; moderate/override grades; review appeals/interventions; report. | Only assigned SubjectInstances and their enrolled Students, attempts, mastery, engagement, and alerts; shared Subject artifacts where assigned. |
| Student | Learner | Provide personal scheduling preferences and complete assigned learning activities. | View assigned Subjects; set availability/preferences/blackouts; take opened assessments; follow plans; use Tutor; practice; view feedback/mastery/recommendations/deficit; appeal any formative grade. | Own profile, enrollments, plans, attempts, grades, mastery display, recommendations, notifications, and supportive messages. No peer data or internal risk labels. |

## 7. Role-Permission Matrix

Legend: `C` Create, `V` View, `U` Update, `D` Delete, `A` Approve, `T` Trigger, `M` Moderate, `E` Export, `-` No permission. All permissions are restricted by the actor's scope in Section 6. Delete means controlled deletion/deactivation only where data integrity permits.

| Module / Data | Admin | Teacher | Student |
|---|---|---|---|
| Department | C/V/U/D | V (own) | V (own label) |
| Programs | C/V/U/D | V | V (own) |
| Batches | C/V/U/D | V | V (own) |
| Semesters | C/V/U/D | V | V (own) |
| Sections | C/V/U/D | V (assigned) | V (own) |
| Subjects / elective allocation | C/V/U/D | V (assigned) | V (assigned, read-only) |
| Students / enrollment | C/V/U/D | V (assigned sections) | V (self); U own preferences only |
| Content | V | C/V/U/version (assigned); A/rollback (Subject Owner) | V approved assigned content |
| Curriculum / topic graph | V | C/V/U (assigned); A (Subject Owner) | V approved structure |
| Question Bank | V | C/V/U (assigned); A (Subject Owner) | No direct bank view; served items only |
| Coverage | V | V/U (assigned, audited) | V where exposed in plans |
| Attendance / ClassSession | V/report | C/V/U (assigned) | - |
| Diagnostics | T/V (prerequisite) | C/T/V (checkpoint, assigned) | V/take when opened; cannot trigger |
| Grading | V audit/report | V/M/override (assigned) | V own; appeal any formative grade |
| Study Plan | V aggregate | V assigned Students; SubjectInstance pin | V own |
| Tutor | V logs where authorized | V assigned usage/citations | Use for assigned Subject, subject to lockdown |
| Reports | V/E institution | V/E assigned sections | V own summaries; no institutional export |
| Interventions | V aggregate | V/U/resolve assigned | V own supportive message only |
| Notifications | V institution alerts | V own assigned alerts | V own notifications |

## 8. System Modules

| ID | Module | Purpose |
|---|---|---|
| M01 | Authentication & User Management | JWT login, password security, role assignment, and scoped access. |
| M02 | Institution & Academic Setup | Institute, department, program, batch, semester, and section setup. |
| M03 | Subject & Student Allocation | Program-scoped Subjects, Subject Owners, SubjectInstances, Teacher assignments, capacity-aware electives, import, promotion, and auto-enrollment. |
| M04 | Academic Calendar & Timetable | Institution timezone, term/holiday/exam constraints, exact SubjectInstance exam dates, and recurring Section class/lab timetable. |
| M05 | Content Management | Upload, validation, ingestion, storage, metadata, versions, rollback, and approval status. |
| M06 | Curriculum & Topic Graph | AI extraction, deterministic graph checks, editing, approval, and fallback. |
| M07 | Question Bank | Generation, critique, teacher approval, item quality, and exposure management. |
| M08 | Coverage Tracker | Per topic and subject-section teaching status and history. |
| M09 | Diagnostic Assessment | Prerequisite/checkpoint session control and deterministic adaptive item selection. |
| M10 | Grading | Common objective, numerical, coding, and subjective grading plus moderation/appeal. |
| M11 | Learner Model | Exact Mastery Score, confidence, prior, manual attendance input, Engagement Score, and insufficient-evidence behavior. |
| M12 | Adaptive Study Planner | Eligibility, priority, ordering, feasibility, triage, packing, revision, and explanation. |
| M13 | Daily Learning | Daily/weekly plan views and approved material consumption. |
| M14 | RAG Tutor | Subject-scoped cited answers with refusal and assessment-session lockdown guardrails. |
| M15 | Practice & Quiz | Student-choice/suggested practice and Teacher-configured quizzes using approved exposure-controlled items. |
| M16 | Recommendation | Ranked, topic-mapped approved resources for weak topics. |
| M17 | Intervention | Evidence-based teacher-first alerts and supportive student messages. |
| M18 | Dashboards, Notifications & Reports | Role-scoped operational views, persistent in-app notifications, daily snapshots, analytics, and PDF/Excel exports. |

## 9. End-to-End System Workflow

The workflow uses 16 primary stages and two blocking approval half-stages.

| Stage | Actor | Trigger | Input | Main Process | Output | Next Stage |
|---|---|---|---|---|---|---|
| 1. Institution & Department Setup | Admin | Project/term setup | Institute, departments, programs, batches, semesters, sections, timezone, calendar, exam dates, timetable, staff | Validate hierarchy, dates, capacities, and Teacher accounts. | Complete active academic hierarchy and scheduling calendar | 2 |
| 2. Subject Catalogue & Allocation | Admin | Academic setup complete | Program-scoped Subjects, type, credits, unit weights, elective groups/capacities, sections, Teachers, Student CSV | Create SubjectInstances; designate one PRIMARY Teacher as shared Subject Owner and assign PRIMARY/CO Teachers to instances; allocate exactly one required elective; auto-enroll Students by Program + Semester + Section. | Admin-approved authoritative Student Subject lists | 3 |
| 3. Content Ingestion | Teacher + IngestionService | Assigned Teacher upload | Syllabus, notes, PPT, PYQ, links, lab manuals | Validate, OCR if scanned, clean, semantically chunk, embed, and store a new immutable DRAFT version; keep active version unchanged. | Traceable content version and chunks | 4 |
| 4. Curriculum Generation | Curriculum Agent + deterministic checks | Syllabus ingestion complete | Syllabus chunks and unit structure | Extract topics/outcomes/Bloom/time/weight/prerequisites/confidence; detect cycles/orphans/duplicates. | Draft topic graph plus validation flags | 4.5 |
| 4.5 Teacher Approval Gate | Subject Owner | Draft graph available | Draft graph and flags | Review assigned-Teacher edits; approve/reject the immutable version; explicitly choose flat fallback only if no prior active chain exists. | New ACTIVE graph/fallback, or unchanged prior ACTIVE version | 5 |
| 5. Question Generation & Critique | Assessment Agent + Critic Agent | Approved Topics available | Assigned-Teacher blueprint, approved Topics/source chunks, and item budget up to 200 | Batch-generate applicable items; critique ambiguity, distractors, alignment, scope, duplicates, and rubrics. | DRAFT traceable QuestionBankVersion | 5.5 |
| 5.5 Question Bank Approval | Subject Owner | Critiqued items available | Topic/type/difficulty-stratified 10% sample and Critic results | Review sample; any critical failure returns the version for correction and resampling; approve only a compliant version. | READY QuestionBankVersion | 6 |
| 6. Student Onboarding | Student | Login after allocation | Auto-enrollments and Student preferences | Show read-only Subjects; collect recurring 30-minute availability, preferred time, blackouts, and learning preference. | Scheduling profile | 7 |
| 7. Coverage and Attendance Tracking | Teacher | Teaching activity | Approved Topic list, ClassSession, lecture progress, enrolled roster | Update coverage with audited corrections; record PRESENT/ABSENT per ClassSession; warn on uncovered prerequisites; replan affected Students. | Current SubjectInstance coverage and attendance | 8/10/11 |
| 8A. Prerequisite Diagnostic | Admin | First 14 semester days | One Program/Semester/Subject offering, earlier-semester prerequisite Topics, target Sections, window, duration, and max items | Validate the single offering session and its maximum five Topics; DiagnosticEngine adaptively selects exposed-safe items. | Raw response set | 9 |
| 8B. Coverage Checkpoint | Teacher | Teacher decides after coverage | Only `COVERED`/`REVISED` Topics, Sections, window, duration, supervision, and sufficient item budget | Validate scope; open session; DiagnosticEngine adaptively selects items. | Raw response set | 9 |
| 9. Common Grading | AutoGrader + Grading Agent + Teacher when needed | Diagnostic, quiz, or practice submission | Item response, answer key/tolerance/test cases/rubric | Grade by type; identify misconceptions; hold low-confidence subjective or appealed evidence until resolution. | Uniform finalized or pending ItemResponse evidence | 10 |
| 10. Learner Model | LearnerModelService | Final valid evidence or behavior change | Valid nonsuspect Topic evidence and available behavior components | Calculate raw/effective mastery and confidence; calculate separate full or labeled-partial engagement. | TopicMastery and EngagementScore | 11 |
| 11. Adaptive Planning | StudyPlannerService | Nightly or qualifying event | Approved graph, actual coverage, mastery, exact exam dates, Section timetable, 30-minute availability, pins, pending/missed work | Build one deadline-aware cross-subject plan, check cumulative feasibility, triage, pack 30-minute blocks, and schedule revision. | Daily/weekly plan and one grouped CoverageDeficit | 12 |
| 12. Daily Learning & Tutor | Student + Tutor Agent | Student opens today's plan/material/tutor | Plan slot, approved material, student question | Present learning activity; retrieve approved chunks and answer with citations, subject to lockdown. | Completed/attempted activity and cited help | 13/14 |
| 13. Practice & Quiz | Teacher or Student | Teacher opens a quiz or Student starts self-practice | READY items filtered by Topic, blueprint/difficulty, and exposure | Serve reproducibly randomized items, submit through common grading, update mastery, and replan on qualifying change. | Feedback and new evidence | 9 -> 10 -> 11 |
| 14. Recommendation | Recommendation function of combined Agent | Weak topic or nightly run | Weak topics, preference, time, approved resources | Rank topic-mapped resources. | Specific approved-material recommendations | 12/15 |
| 15. Intervention | Combined Recommendation + Intervention Agent, Teacher | Nightly detection | Mastery trend, engagement, missed sessions, prerequisite gaps | Create evidence-based teacher alert; teacher reviews; issue supportive student nudge where appropriate. | Reviewed/resolved alert and supportive message | 16 |
| 16. Dashboards & Reports | Teacher, Admin | Live view or end of semester | Coverage, evidence, mastery, engagement, alerts, item analysis | Aggregate within role scope; filter and export defined reports. | Operational dashboards and PDF/Excel reports | Ongoing/term close |

## 10. Business Requirements

| ID | Name | Requirement | Actor | Reason | Priority |
|---|---|---|---|---|---|
| BR-001 | Authoritative Academic Structure | The college shall maintain its department, Program, batch, semester, Section, Program-scoped Subject, exact exam, timetable, and calendar structure in the platform. | Admin | All allocation and academic scope depend on this hierarchy. | Must Have |
| BR-002 | Automatic Subject Enrollment | Student Subjects shall be determined only by Program + Semester + Section, with Admin-controlled capacity-aware elective allocation. | Admin, Student | Prevent invalid/self-selected academic registrations. | Must Have |
| BR-003 | Approved Content Foundation | Academic AI functions shall use immutable, versioned, traceable Subject-level course content activated by the Subject Owner. | Teacher | Keep outputs within the curriculum and traceable. | Must Have |
| BR-004 | Human-Approved Curriculum | AI-generated Topics and prerequisite relationships shall not become live until the Subject Owner approves the version. | Teacher | Prevent invalid graphs from affecting learning. | Must Have |
| BR-005 | Human-Approved Question Bank | Generated Questions shall not be served until the bank passes Critic checks, required sample review, and Subject Owner approval. | Teacher | Protect assessment quality. | Must Have |
| BR-006 | Actual Coverage Control | The platform shall record actual topic coverage per subject-section and use it in diagnostics and planning. | Teacher | Align adaptive behavior with teaching reality. | Must Have |
| BR-007 | Controlled Diagnostics | Only an Admin may trigger Prerequisite Diagnostics and only an assigned Teacher may trigger Coverage Checkpoints; Students shall only take opened sessions. | Admin, Teacher, Student | Preserve diagnostic timing and academic control. | Must Have |
| BR-008 | Common Grading Flow | Every diagnostic, quiz, and practice response shall use the same grading path appropriate to its item type. | System, Teacher | Produce consistent evidence. | Must Have |
| BR-009 | Knowledge-Only Mastery | Topic mastery shall use only graded knowledge evidence with difficulty, source, recency, evidence, confidence, and prior. | Student, Teacher | Avoid misleading mastery and plans. | Must Have |
| BR-010 | Separate Engagement | Attendance, adherence, revision consistency, and on-time submission shall form a separate score used only in interventions and teacher dashboards. | Teacher | Separate behavior from knowledge. | Must Have |
| BR-011 | Feasible Adaptive Plan | Plans shall use the approved graph, real coverage, mastery, calendar, and availability and shall disclose any workload deficit. | Student, Teacher | Avoid silently incomplete plans. | Must Have |
| BR-012 | Grounded Tutor | The Tutor shall answer only from approved subject content, cite sources, and prevent active-assessment answer leakage. | Student, Teacher | Reduce hallucination and assessment gaming. | Must Have |
| BR-013 | Deterministic Coding Evaluation | Coding correctness shall be established by isolated test-case execution. | Student, Teacher | Make code scores reproducible and safe. | Must Have |
| BR-014 | Grade Oversight | Low-confidence subjective grades and Student appeals of any formative grade shall reach Teacher moderation with recorded outcomes. | Teacher, Student | Maintain human accountability. | Must Have |
| BR-015 | Approved Recommendations | Recommendations shall map weak topics to ranked, approved course material. | Student | Keep remediation relevant and in scope. | Should Have |
| BR-016 | Teacher-First Intervention | Potential concerns shall go to the Teacher first; students shall receive specific supportive messages, not risk labels. | Teacher, Student | Avoid harmful or premature labeling. | Should Have |
| BR-017 | Role-Scoped Visibility | Each actor shall see only data allowed by role and academic scope. | All | Protect privacy and academic boundaries. | Must Have |
| BR-018 | Academic Reporting | The platform shall provide achievable coverage, performance, mastery, and attendance reports with PDF/Excel export. | Admin, Teacher | Support review and project demonstration. | Should Have |

## 11. Business Rules

| Rule ID | Rule | Actor | Related Module | Validation / Enforcement |
|---|---|---|---|---|
| BUS-001 | Students must never manually select, add, or drop subjects. | Student, Admin | M03 | No student enrollment mutation UI/API; unauthorized request returns `403`. |
| BUS-002 | Enrollment is auto-derived from Program + Semester + Section; Admin assigns exactly one eligible Subject in each required elective group within offering capacity. | Admin | M03 | Allocation service creates `Enrollment.auto_allocated=true`; validate required core and elective coverage. |
| BUS-003 | One Prerequisite Diagnostic version per Program/Semester/Subject offering may be triggered only by Admin within the first 14 calendar days of the Semester and may target multiple Sections. | Admin | M09 | RBAC, offering uniqueness, Topic, Section, and term-date validation. |
| BUS-004 | Coverage Checkpoint Diagnostics may be triggered only by an assigned Teacher. | Teacher | M09 | RBAC and subject-section assignment query filter. |
| BUS-005 | Students cannot create or trigger any diagnostic. | Student | M09 | No UI control; API rejects request with `403`. |
| BUS-006 | A checkpoint scope may contain only Topics whose current state is `COVERED` or `REVISED` in every targeted SubjectInstance. | Teacher | M08, M09 | Creation transaction rejects and names every offending Topic/Section pair. |
| BUS-007 | DiagnosticEngine selects and serves questions; it never grades answers. | System | M09, M10 | Separate service boundary and tests; raw responses handed to common grading. |
| BUS-008 | All attempt sources use the common grading flow. | System | M10 | Source-agnostic grading entry point and uniform `ItemResponse` record. |
| BUS-009 | MCQ/True-False use exact key matching; numerical items use a per-Question absolute tolerance in the expected unit. | System | M10 | AutoGrader applies `abs(submitted - expected) <= absolute_tolerance`; default tolerance is `0`. |
| BUS-010 | Coding correctness uses an isolated sandbox and deterministic test cases; LLM may only comment on style/approach. | System | M10 | No LLM score path for code correctness; sandbox has CPU/memory/time/network limits. |
| BUS-011 | Subjective answers may use rubric-driven LLM grading with score, rationale, breakdown, and confidence. | System | M10 | Strict structured output schema and rubric requirement. |
| BUS-012 | Subjective grade confidence below `0.7` requires Teacher moderation and cannot enter mastery until resolved. | Teacher | M10 | Automatic moderation queue and evidence-status rule. |
| BUS-013 | A Student may appeal any formative score. | Student, Teacher | M10 | Appeal creates a moderation item; appealed evidence is withheld from mastery until the audited decision. |
| BUS-014 | All platform grades are formative and shall not update official university marks. Teacher moderation produces a verified formative grade only. | Teacher | M10 | Grade purpose/status is fixed to formative; official mark integration is out of scope. |
| BUS-015 | Mastery contains knowledge evidence only. | System | M11 | Formula inputs limited to graded item evidence. |
| BUS-016 | Attendance, plan adherence, revision consistency, and on-time submission belong only to Engagement Score. | System | M11 | Separate computation and storage. |
| BUS-017 | Engagement Score must never affect Mastery Score. | System | M11 | Learner-model interface and unit tests exclude engagement fields. |
| BUS-018 | Engagement Score must never affect Study Planner eligibility or priority. | System | M12 | Planner interface accepts mastery/confidence but not engagement. |
| BUS-019 | Numeric mastery is displayed only when confidence is at least `0.35` and at least five final valid responses exist; otherwise the UI displays `Building your profile`. | Student | M11 | API/UI display-state rule. |
| BUS-020 | A shared Subject curriculum version requires explicit Subject Owner approval before becoming `ACTIVE`; approved versions are immutable. | Teacher | M06 | Owner authorization and version state-transition guard. |
| BUS-021 | Cycle detection, orphan detection, and duplicate detection run before Topic-graph approval. | System | M06 | DFS, orphan validation, and active versioned embedding threshold/model (initial threshold `>0.92`). |
| BUS-022 | For a detected cycle, the lowest-confidence edge is dropped and flagged; runtime recurrence falls back to unit order and is logged. | System, Teacher | M06, M12 | Deterministic graph processing plus incident record. |
| BUS-023 | Subject Owner rejection leaves any prior ACTIVE curriculum unchanged; only when no prior active version exists may the Owner explicitly activate flat syllabus Unit order without cross-Topic prerequisites. | Teacher, System | M06 | Active pointer/fallback guards keep the platform operable without replacing valid content automatically. |
| BUS-024 | A QuestionBankVersion requires a Topic/type/difficulty-stratified 10% sample, correction and resampling after any critical failure, Subject Owner approval, and `READY` status before use; approved versions are immutable. | Teacher | M07 | Owner authorization, sample evidence, and serving status filter. |
| BUS-025 | Questions are generated in batch from an assigned-Teacher-configured blueprint; the active generation cap is configurable but cannot exceed 200 items per batch, and generation never occurs during a live test. | System | M07 | Celery batch job, configured-cap validation, and READY-bank-only serving. |
| BUS-026 | After at least 30 final valid responses for the same Question version, compute p-value and point-biserial discrimination against assessment total excluding that item; `p < 0.15` or negative discrimination makes the item suspect and triggers affected mastery recomputation. | Teacher, System | M07, M11 | Item-analysis status and Learner Model evidence invalidation. |
| BUS-027 | Tutor responses use approved uploaded Subject material only and include resolvable citations; uncrawled HTTPS references are recommendation-only. | Student | M14 | Retrieval filter by Subject/version/approval and response citation validation. |
| BUS-028 | During an assessment, Tutor remains concept-only until the complete session closes and blocks item answers, worked results, code solutions, and queries meeting the configured active-Question similarity threshold. | Student | M14 | Session-wide guard plus versioned embedding-model threshold configuration. |
| BUS-029 | Planner eligibility and priority follow the exact algorithm in Section 25. | System | M12 | Pure deterministic implementation with formula unit tests. |
| BUS-030 | Planner performs deadline-aware cumulative feasibility checking across all Subjects before slot packing and never silently removes a Topic. | System | M12 | Count each 30-minute availability block once; all unscheduled eligible Topics appear in `CoverageDeficit`. |
| BUS-031 | If time is insufficient, both Student and assigned Teachers receive one Student-level Coverage Deficit grouped by SubjectInstance and deadline, and the plan is labeled `TRIAGE`. | Student, Teacher | M12 | Persist grouped totals and unscheduled Topic IDs. |
| BUS-032 | Planner uses exact SubjectInstance exam dates, Section timetable, holidays, recurring 30-minute availability, and blackouts when computing capacity. | System, Student, Admin | M04, M12 | Calendar intersection/subtraction and no-double-count tests. |
| BUS-033 | Teacher coverage state is one of `NOT_STARTED`, `IN_PROGRESS`, `COVERED`, `REVISED`; forward and backward corrections are allowed, with confirmation for backward changes, audit, and immediate replanning. | Teacher | M08 | Enum, transition confirmation, audit, and event tests. |
| BUS-034 | Marking a topic covered while a prerequisite is `NOT_STARTED` generates a warning but is not blocked. | Teacher | M08 | Non-blocking prerequisite check and stored update. |
| BUS-035 | The planner schedules `COVERED`/`REVISED` topics, and an `IN_PROGRESS` topic only when every prerequisite has effective mastery at least `0.6`. | System | M08, M12 | Eligibility predicate. |
| BUS-036 | Intervention alerts route to the Teacher first; Students never see an `at risk` label or peer alerts. | Teacher, Student | M17 | Visibility/status rules and approved supportive copy. |
| BUS-037 | AI outputs, approvals, grade changes, and Teacher overrides are versioned, source-traceable, and logged with minimized pseudonymous Student data for external AI calls. | System, Teacher | Cross-cutting | `agent_runs`, version records, privacy filter, and audit log. |
| BUS-038 | If coverage is not updated for seven days, notify the assigned Teacher and Admin in-app; the Planner continues using the last actual coverage and never invents projected states. | Teacher, Admin | M08, M12, M18 | Staleness job, notifications, and actual-state-only planner test. |
| BUS-039 | A new upload creates an immutable DRAFT Subject-level version and never overwrites active content; only the Subject Owner may activate or roll back, and the existing active curriculum/bank chain remains usable until approved replacements activate. | Teacher | M05, M06, M07 | Immutable versions, owner guard, dependency links, and active pointers. |
| BUS-040 | Long-running generation/ingestion jobs are retryable and resumable; objective grading remains available during LLM outage. | System | M05, M07, M10 | Idempotent Celery tasks and deterministic fallback paths. |
| BUS-041 | Attendance is entered manually by an assigned Teacher for each dated/timed ClassSession and enrolled Student. | Teacher | M11, M18 | ClassSession-scoped present/absent entry with actor/time audit; no ERP integration. |
| BUS-042 | Lab subjects are excluded from adaptive planning and support only setup, content, coverage, attendance, and reports in this project. | Admin, Teacher, Student | M03, M05, M08, M11, M18 | Subject type filter prevents lab Topics from entering StudyPlannerService. |
| BUS-043 | The system supports exactly `ADMIN`, `TEACHER`, and `STUDENT`; Admin designates one PRIMARY Teacher as Subject Owner, and every other assigned Teacher, whether PRIMARY or CO, has full assigned-instance operations except final shared-artifact activation. | Admin, Teacher | M01, M03, M05-M07 | Role enum, ownership constraint, and authorization tests. |
| BUS-044 | Teacher-created quizzes and Student self-practice are the only non-diagnostic assessment sources; assignments are not supported. | Teacher, Student | M09, M15 | Source-type enum and absent assignment UI/API. |
| BUS-045 | Planner work and revision use 30-minute blocks; Topics may span multiple blocks, every revision consumes 30 minutes, and revision capacity is included in feasibility. | System | M12 | Packing and boundary tests. |
| BUS-046 | Planner regenerates nightly and after evidence/mastery, coverage, availability/preference/blackout, exam/timetable, SubjectInstance pin, missed-slot, or plan-completion events. | System | M12 | Debounced idempotent event-trigger matrix. |
| BUS-047 | HTTPS reference links are stored as approved recommendation metadata only and are never crawled, embedded, or used as Tutor evidence. | Teacher, Student | M05, M14, M16 | Resource-type filters. |
| BUS-048 | In-app notifications are persistent and scoped to the recipient, with read/unread state. | All | M18 | Ownership, delivery, and state tests. |
| BUS-049 | Admin bulk promotion/Section transfer preserves historical enrollments and previews the new authoritative set before confirmation. | Admin | M03 | Preview/confirm transaction and history tests. |
| BUS-050 | Embedding similarity thresholds are stored with the embedding-model version and must be revalidated before a new model version becomes active. | System, Admin | M05-M07, M14 | Configuration/version guard. |

## 12. Functional Requirements

Each entry uses the required structure in compact form. `Pre` = Precondition, `Val` = Validation, `Post` = Postcondition, and `AC` = Acceptance Criteria. Cross-referenced acceptance scenarios are detailed in Section 40.

### 12.1 Authentication and Role Access

| Requirement ID / Name | Actor / Priority | Requirement Detail |
|---|---|---|
| FR-AUTH-001 - Secure Login and Revocation | All / Must Have | **Description:** The system shall authenticate active users and issue a four-hour JWT containing identity, exactly one supported role, and token-version claims; no refresh token is issued.<br>**Pre:** Account exists and is active.<br>**Trigger:** Login, logout, deactivation, or protected request.<br>**Input:** Username/email, password, account state, and token version.<br>**Processing:** Verify bcrypt hash; issue JWT; validate current account/token version on protected requests; increment the token version on logout or deactivation.<br>**Val:** Invalid/inactive credentials and revoked/expired tokens are rejected without disclosing credential details.<br>**Output:** Role-appropriate session or authorization error.<br>**Post:** Logout or deactivation invalidates issued access immediately.<br>**AC:** AC-001. |
| FR-AUTH-002 - Role and Scope Enforcement | All / Must Have | **Description:** The system shall enforce RBAC and department/section/ownership scope at the route and query layers.<br>**Pre:** Authenticated request.<br>**Trigger:** Any protected operation.<br>**Input:** Token, requested action, resource scope.<br>**Processing:** Resolve role and authorized records before the business action.<br>**Val:** Students=self; Teachers=assigned SubjectInstances/sections; Admin=institution scope.<br>**Output:** Authorized result or `403`.<br>**Post:** No unauthorized data is read or changed.<br>**AC:** AC-001. |
| FR-AUTH-003 - Account Administration | Admin / Must Have | **Description:** The system shall allow Admin to create, view, update, activate, and deactivate Teacher and Student accounts. Every account shall have exactly one role from `ADMIN`, `TEACHER`, or `STUDENT`.<br>**Pre:** Admin authenticated.<br>**Trigger:** Account maintenance action.<br>**Input:** Identity, role, department/section references, active state.<br>**Processing:** Validate unique identity and references; hash initial/reset password.<br>**Val:** Role and scope assignment must be valid.<br>**Output:** Account record.<br>**Post:** Audit record created.<br>**AC:** A deactivated account cannot log in. |
| FR-AUTH-004 - Invitation, Reset, and Login Throttling | Admin, All / Must Have | **Description:** The system shall let Admin generate single-use expiring account invitation/password-reset URLs for secure out-of-band delivery, let the intended user consume them, and throttle repeated failed login/token attempts.<br>**Pre:** Admin creates or selects the account.<br>**Trigger:** Admin token generation, user token consumption, or repeated authentication failure.<br>**Input:** Account identity and single-use token.<br>**Processing:** Store only token hashes, enforce expiry/use-once behavior, invalidate earlier reset tokens, and apply account/IP-aware throttling.<br>**Val:** A public response must not reveal whether an identity exists; email/SMS delivery is not required.<br>**Output:** One-time URL to Admin, activation/reset result to user, or generic failure.<br>**Post:** Password reset increments `token_version`; security actions are audited without logging token secrets.<br>**AC:** Used/expired/replaced tokens fail and throttling does not expose credentials. |

### 12.2 Admin Requirements

| Requirement ID / Name | Actor / Priority | Requirement Detail |
|---|---|---|
| FR-ADM-001 - Academic Hierarchy | Admin / Must Have | **Description:** The system shall let Admin create, view, update, and safely deactivate Institute, Department, Program, Batch, Semester, and Section records in the defined hierarchy.<br>**Pre:** Admin authenticated.<br>**Trigger:** Setup action.<br>**Input:** Codes, names, duration, years, semester number/dates, section capacity.<br>**Processing:** Persist parent-child relationships.<br>**Val:** Required fields, unique codes within parent, valid year/date ranges, positive capacity.<br>**Output:** Updated hierarchy.<br>**Post:** Records are available for allocation.<br>**AC:** A Section cannot be created without a valid semester/batch path. |
| FR-ADM-002 - Teacher and Subject Owner Assignment | Admin / Must Have | **Description:** The system shall assign one or more Teachers as `PRIMARY` or `CO` to SubjectInstances and designate exactly one PRIMARY Teacher as Subject Owner for each active Subject offering.<br>**Pre:** Teacher accounts, Subject, and SubjectInstances exist.<br>**Trigger:** Admin assignment.<br>**Input:** Teacher, Subject/SubjectInstance, assignment role, and owner flag.<br>**Processing:** Create/update scoped assignments.<br>**Val:** Account role is `TEACHER`; every active SubjectInstance has a Teacher; exactly one owner exists; owner is PRIMARY on at least one related instance.<br>**Output:** TeacherAssignment and SubjectOwnerAssignment.<br>**Post:** Operational and approval permissions update.<br>**AC:** AC-001 and AC-002. |
| FR-ADM-003 - Subject Catalogue | Admin / Must Have | **Description:** The system shall maintain Program + Semester scoped Subjects with code, name, credits, type, elective group where applicable, and Unit exam weightage.<br>**Pre:** Program and semester structure exists.<br>**Trigger:** Subject maintenance.<br>**Input:** Subject and Unit attributes.<br>**Processing:** Create/update catalogue and Units.<br>**Val:** Unique code in Program/Semester scope; supported type; nonnegative credits; Unit weights each `0..100` and total exactly `100`; elective membership matches type.<br>**Output:** Subject record.<br>**Post:** Subject can be instantiated for a Section in the same Program/Semester.<br>**AC:** Invalid scope, duplicate code, or invalid weights are rejected. |
| FR-ADM-004 - Subject-Section and Teacher Allocation | Admin / Must Have | **Description:** The system shall map a Subject to a Section as a `SubjectInstance` and allocate Teacher(s).<br>**Pre:** Subject, Section, and Teacher exist.<br>**Trigger:** Admin maps offering.<br>**Input:** Subject ID, Section ID, Teacher IDs/roles.<br>**Processing:** Create DRAFT instance and assignments.<br>**Val:** Subject Program/Semester matches the Section path; no duplicate instance; at least one assigned Teacher before activation.<br>**Output:** SubjectInstance and TeacherAssignment records.<br>**Post:** Content setup can begin.<br>**AC:** AC-002 includes successful appearance in affected Student lists after enrollment. |
| FR-ADM-005 - Student CSV Import | Admin / Must Have | **Description:** The system shall import Students in bulk from CSV and report row-level successes and validation failures.<br>**Pre:** Department, batch, semester, and section exist.<br>**Trigger:** Admin uploads CSV.<br>**Input:** Roll number, identity/account fields, department, batch, current semester, section.<br>**Processing:** Validate rows, avoid duplicates, create/update allowed student records.<br>**Val:** Required columns, unique roll number, valid references and section capacity.<br>**Output:** Import summary and error file/list.<br>**Post:** Valid Students exist; invalid rows do not create partial records.<br>**AC:** A mixed file imports valid rows and names invalid row reasons. |
| FR-ADM-006 - Enrollment, Electives, and Promotion | Admin / Must Have | **Description:** The system shall auto-enroll Students from Program + Semester + Section, assign exactly one eligible Subject per required elective group within offering capacity, and support previewed bulk promotion/Section transfer without erasing history.<br>**Pre:** Active offerings and Student placement exist.<br>**Trigger:** Import, elective allocation, promotion/transfer, or enrollment refresh.<br>**Input:** Placement, capacities, and Admin elective assignment.<br>**Processing:** Preview the authoritative set, validate capacity, confirm atomically, close prior active enrollments where needed, and create idempotent `auto_allocated=true` enrollments.<br>**Val:** No duplicates, mismatches, capacity overflow, or missing required elective.<br>**Output:** Read-only current Subject list plus preserved history.<br>**Post:** Allocation is audited.<br>**AC:** AC-002. |
| FR-ADM-007 - Academic Calendar, Exams, and Timetable | Admin / Must Have | **Description:** The system shall manage institution timezone, term dates, holidays, IA/practical/university windows, exact SubjectInstance exam dates, and recurring Section class/lab slots.<br>**Pre:** Semester, Sections, and SubjectInstances exist.<br>**Trigger:** Calendar/timetable maintenance.<br>**Input:** Dates, windows, exact exams, and recurring start/end slots.<br>**Processing:** Store normalized timezone-aware constraints.<br>**Val:** Start precedes end; dates lie in term; exact exams lie in their applicable window; overlapping mandatory events are rejected.<br>**Output:** Complete planning calendar/timetable.<br>**Post:** Planner can compute deadlines and free 30-minute blocks without double counting.<br>**AC:** AC-003. |
| FR-ADM-008 - Prerequisite Diagnostic Trigger | Admin / Must Have | **Description:** The system shall allow Admin to create one versioned Prerequisite Diagnostic per Program/Semester/Subject offering, target one or more Sections, and open it only within the first 14 calendar days of the Semester.<br>**Pre:** Earlier-semester prerequisite Topics and sufficient READY Questions exist.<br>**Trigger:** Admin configures session.<br>**Input:** Offering, Sections, up to five Topics, window, duration, item budget, and supervision flag.<br>**Processing:** Validate uniqueness, scope, timing, blueprint, exposure, and sufficient item capacity; schedule/open.<br>**Val:** Maximum 40 items; at least five eligible items per Topic when supervised or six when unsupervised; source weight remains `0.9`.<br>**Output:** PREREQ DiagnosticSessionVersion.<br>**Post:** Eligible Students receive one attempt.<br>**AC:** AC-010. |
| FR-ADM-009 - Institution Reporting | Admin / Should Have | **Description:** The system shall provide institution-level Department/Semester rollups and defined exports from current data or daily snapshots.<br>**Pre:** Report data exists.<br>**Trigger:** Admin opens/exports report.<br>**Input:** Department, Semester, batch, Subject, and date filters.<br>**Processing:** Apply confidence-weighted aggregation, included/excluded counts and bands, and group-size suppression.<br>**Val:** Valid filters; selected group under five suppresses aggregate but not authorized row-level access.<br>**Output:** Dashboard/table/PDF/Excel.<br>**Post:** Export event is logged.<br>**AC:** AC-024. |

### 12.3 Teacher and Student Core Requirements

| Requirement ID / Name | Actor / Priority | Requirement Detail |
|---|---|---|
| FR-TCH-001 - Assigned Teaching Workspace | Teacher / Must Have | **Description:** The system shall list only assigned SubjectInstances and provide their content, graph, bank, coverage, assessment, grade, learner, and report tools.<br>**Pre:** TeacherAssignment exists.<br>**Trigger:** Teacher login/workspace view.<br>**Input:** Authenticated Teacher.<br>**Processing:** Query by assignment.<br>**Val:** Unassigned instances excluded and inaccessible.<br>**Output:** Teaching workspace.<br>**Post:** None.<br>**AC:** Direct access to an unassigned instance returns `403` or `404` without data. |
| FR-TCH-002 - SubjectInstance Topic Pin | Teacher / Should Have | **Description:** The system shall allow an assigned Teacher to pin an approved Topic for planner priority across the complete SubjectInstance.<br>**Pre:** Approved Topic and assigned SubjectInstance.<br>**Trigger:** Teacher sets/removes pin.<br>**Input:** Topic, SubjectInstance, and pin state.<br>**Processing:** Store `teacher_pin` as 1 or 0 and emit a replan event for enrolled Students.<br>**Val:** Topic belongs to the Subject and the pin never bypasses eligibility.<br>**Output:** Updated pin state.<br>**Post:** Next plan run uses the 0.05 contribution.<br>**AC:** A pinned eligible Topic receives exactly the contribution, not guaranteed top placement. |
| FR-TCH-003 - ClassSession Attendance | Teacher / Must Have | **Description:** The system shall allow an assigned Teacher to create or select a dated/timed ClassSession and record every enrolled Student as `PRESENT` or `ABSENT`.<br>**Pre:** Teacher assignment, SubjectInstance timetable, and roster exist.<br>**Trigger:** Teacher opens attendance for a current/past ClassSession and saves.<br>**Input:** ClassSession and Student states.<br>**Processing:** Validate roster and atomically upsert one record per Student/session.<br>**Val:** Assigned scope only; future sessions and non-enrolled Students are rejected; correction preserves audit history.<br>**Output:** Attendance records and session summary.<br>**Post:** Attendance rate/report inputs are available.<br>**AC:** AC-028. |
| FR-STU-001 - Read-Only Assigned Subjects | Student / Must Have | **Description:** The system shall display the Student's auto-enrolled subjects without add/drop controls.<br>**Pre:** Student authenticated and enrollments exist.<br>**Trigger:** Student opens subjects.<br>**Input:** Student identity.<br>**Processing:** Query own authoritative enrollments.<br>**Val:** No mutation endpoint permitted.<br>**Output:** Subject list.<br>**Post:** None.<br>**AC:** AC-002. |
| FR-STU-002 - Scheduling Preferences | Student / Must Have | **Description:** The system shall allow the Student to select recurring 30-minute weekly availability blocks in the institution timezone, preferred time-of-day, personal blackout dates, and learning preference (`video`, `text`, `practice-heavy`, `mixed`).<br>**Pre:** Student authenticated.<br>**Trigger:** Save preferences.<br>**Input:** Availability grid, preferred slot, dates, and learning preference.<br>**Processing:** Validate, version, persist, and emit a replan event.<br>**Val:** No overlaps/invalid dates and no exam/timetable edits.<br>**Output:** StudentPreference.<br>**Post:** Next plan uses the new profile.<br>**AC:** AC-027. |
| FR-STU-003 - Scheduled Assessment Participation | Student / Must Have | **Description:** The system shall allow a Student to start, autosave, submit, or time-expire only an assigned Diagnostic or Teacher-created Quiz during its allowed window; Student-initiated practice follows FR-PRC-001.<br>**Pre:** Open eligible session and READY bank.<br>**Trigger:** Student starts/answers/submits.<br>**Input:** Session and responses.<br>**Processing:** Create one attempt, serve selected items, autosave, enforce timer, and submit raw responses.<br>**Val:** Ownership, window, one-attempt limit, and item exposure.<br>**Output:** Submitted StudentAttempt and raw ItemResponses.<br>**Post:** Common grading is invoked and Tutor lockdown remains until the session closes.<br>**AC:** A closed/unassigned session or second attempt cannot be started. |
| FR-STU-004 - Plans and Approved Learning Material | Student / Must Have | **Description:** The system shall show the Student's daily/weekly plan, revision slots, reason per slot, and linked approved material.<br>**Pre:** Plan exists.<br>**Trigger:** Student opens plan/activity.<br>**Input:** Student/date.<br>**Processing:** Load own current plan and approved content links.<br>**Val:** Subject enrollment and active content version.<br>**Output:** Plan/material view.<br>**Post:** Activity status may be recorded for adherence.<br>**AC:** AC-018. |
| FR-STU-005 - Personal Feedback and Mastery | Student / Must Have | **Description:** The system shall show own grading feedback, misconception guidance, and numeric mastery only when confidence is at least `0.35` and at least five final valid responses exist; otherwise show `Building your profile`.<br>**Pre:** Attempt or learner state exists.<br>**Trigger:** Student opens feedback/progress.<br>**Input:** Own evidence.<br>**Processing:** Apply evidence-based display gate.<br>**Val:** No peer/internal alert data or internal prior shown as measured mastery.<br>**Output:** Appropriate progress view.<br>**Post:** None.<br>**AC:** AC-016. |
| FR-STU-006 - Deficit and Grade Appeal | Student / Must Have | **Description:** The system shall show the Student's grouped Coverage Deficit and allow appeal of any formative grade with a mandatory reason.<br>**Pre:** Corresponding record exists.<br>**Trigger:** Student opens deficit/grade or submits appeal.<br>**Input:** Own record and appeal reason.<br>**Processing:** Create `UNDER_APPEAL` moderation state, withhold the evidence from mastery, and notify the assigned Teacher.<br>**Val:** Ownership and one open appeal per grade.<br>**Output:** Deficit view or appeal confirmation.<br>**Post:** Mastery waits for the decision.<br>**AC:** AC-013 and AC-020. |
| FR-STU-007 - Recommendations and Support | Student / Should Have | **Description:** The system shall show approved-material recommendations, supportive Teacher-approved intervention messages, and related in-app notifications.<br>**Pre:** Corresponding records exist.<br>**Trigger:** Student opens dashboard/notification.<br>**Input:** Own scoped records.<br>**Processing:** Enforce source and wording rules.<br>**Val:** No internal risk label or peer data.<br>**Output:** Recommendation/support view.<br>**Post:** Read/unread notification state may update.<br>**AC:** AC-022 and AC-025. |

### 12.4 Content and Curriculum Requirements

| Requirement ID / Name | Actor / Priority | Requirement Detail |
|---|---|---|
| FR-CON-001 - Shared Subject Content Upload | Teacher / Must Have | **Description:** The system shall allow any assigned Teacher to upload PDF, PPTX, DOCX, or UTF-8 TXT syllabus/notes/question papers/lab manuals up to 25 MB or register recommendation-only HTTPS metadata for a shared Subject.<br>**Pre:** Teacher is assigned to a related SubjectInstance.<br>**Trigger:** Upload/link submission.<br>**Input:** File/link metadata, content type, Subject, and Unit.<br>**Processing:** Validate and register a new DRAFT version/resource; HTTPS links are not crawled or embedded.<br>**Val:** Extension/actual MIME, size, HTTPS, non-empty content, and Subject assignment.<br>**Output:** Pending ingestion record or DRAFT recommendation resource.<br>**Post:** File ingestion is queued; active/approved content is unchanged.<br>**AC:** AC-004. |
| FR-CON-002 - Deterministic Ingestion | IngestionService / Must Have | **Description:** The system shall validate, OCR scanned content when required, clean, chunk to at most 800 embedding-model tokens with 120-token overlap without crossing known Unit boundaries, embed, and store uploaded content.<br>**Pre:** Valid upload exists.<br>**Trigger:** Ingestion job.<br>**Input:** Content version.<br>**Processing:** Reproducible pipeline with retry/resume.<br>**Val:** Each stage records success/failure; empty extraction fails clearly; page/unit association is retained.<br>**Output:** File in MinIO, records in PostgreSQL, vectors in pgvector.<br>**Post:** Chunks are retrievable only under correct subject/version/approval scope.<br>**AC:** AC-004. |
| FR-CON-003 - Chunk Metadata and Traceability | System / Must Have | **Description:** The system shall store `subject_id`, `content_version_id`, `unit_no`, `source_file`, page/slide/section locator, and `chunk_type` (`syllabus`, `notes`, `ppt`, `pyq`, or `lab`) on each uploaded-content chunk and link AI outputs to immutable chunk references.<br>**Pre:** Extractable uploaded content.<br>**Trigger:** Chunk creation or AI output.<br>**Input:** Source location and classification.<br>**Processing:** Persist metadata and immutable reference.<br>**Val:** Mandatory locators cannot be null where applicable; external reference links do not create chunks.<br>**Output:** Traceable chunk/output.<br>**Post:** Tutor/Question citations resolve to uploaded content.<br>**AC:** A sampled answer/Question can be traced to version, file, and locator. |
| FR-CON-004 - Immutable Versioning, Activation, and Rollback | Subject Owner / Must Have | **Description:** Every upload creates an immutable-file DRAFT ContentVersion and every link submission creates a DRAFT ApprovedResourceLink; only the Subject Owner may activate/approve either or roll content back to a valid version.<br>**Pre:** Version/resource belongs to the owned Subject.<br>**Trigger:** Activation/approval/rollback decision.<br>**Input:** ContentVersion or resource link and reason.<br>**Processing:** Change active/approval state and preserve dependent history.<br>**Val:** Owner authorization; successful file ingestion; approved content/link metadata is never edited in place.<br>**Output:** Active/approved status.<br>**Post:** Existing curriculum/bank remain active until replacements activate; prior citations remain resolvable; approved links remain recommendation-only.<br>**AC:** AC-005. |
| FR-CUR-001 - Curriculum Version Extraction | Curriculum Agent / Must Have | **Description:** The system shall create a DRAFT Subject-level CurriculumVersion with stable Topic IDs, Units/Topics, outcomes, Bloom level, estimated hours, inherited Unit exam weightage, and intra-/cross-subject prerequisite edges with confidence `0..1`.<br>**Pre:** An active syllabus ContentVersion exists.<br>**Trigger:** Assigned Teacher requests generation.<br>**Input:** Active syllabus chunks and Units.<br>**Processing:** Versioned prompt with strict schema and content-version references.<br>**Val:** Required fields, valid ranges, and earlier-semester cross-subject scope.<br>**Output:** DRAFT CurriculumVersion.<br>**Post:** Deterministic validation runs while current ACTIVE version remains available.<br>**AC:** Required fields validate or the draft fails safely. |
| FR-CUR-002 - Graph Validation | System / Must Have | **Description:** The system shall run DFS cycle detection, orphan detection, and duplicate-Topic detection using the active versioned similarity/embedding-model configuration (initial threshold `>0.92`) before review.<br>**Pre:** Draft graph and validated configuration.<br>**Trigger:** Generation completion or edited graph validation.<br>**Input:** Topics/edges/confidence/unit links and threshold/model version.<br>**Processing:** Drop and flag the lowest-confidence edge per detected cycle; for a tie sort normalized `(topic_id, prereq_topic_id)` ascending and remove the first; repeat until acyclic; flag orphans and duplicates.<br>**Val:** Final review graph is acyclic/unit-linked; changed model/threshold cannot activate before validation.<br>**Output:** Validated draft, flags, and configuration reference.<br>**Post:** Teacher can review.<br>**AC:** AC-006. |
| FR-CUR-003 - Teacher Graph Editing | Teacher / Must Have | **Description:** The system shall allow the assigned Teacher to rename, merge, split, reorder, classify (`Core`, `Optional`, `Self-study`), change estimated hours, and add/delete prerequisite edges.<br>**Pre:** Draft graph available.<br>**Trigger:** Teacher edit.<br>**Input:** Graph change.<br>**Processing:** Save version and rerun validation.<br>**Val:** Stable IDs preserved or mapped where merge/split occurs; no invalid graph approved.<br>**Output:** Revised draft.<br>**Post:** Approval remains pending after material changes.<br>**AC:** A new cycle cannot pass approval validation. |
| FR-CUR-004 - Subject Owner Approval and Fallback | Subject Owner, System / Must Have | **Description:** The system shall activate an immutable Subject-level CurriculumVersion only after explicit Subject Owner approval; rejection leaves any prior ACTIVE version unchanged. If no prior active version exists, the Owner may explicitly activate a versioned flat Unit order without prerequisite edges.<br>**Pre:** Validation completed.<br>**Trigger:** Subject Owner approves/rejects/selects fallback.<br>**Input:** Version, decision, and reason.<br>**Processing:** Audit the decision and atomically update the active pointer only for a valid approval/fallback.<br>**Val:** Owner authorization; no invalid AI graph activates; prior ACTIVE version remains until transition succeeds.<br>**Output:** ACTIVE CurriculumVersion or unchanged prior version plus RETURNED draft.<br>**Post:** Question generation/planning use the active version.<br>**AC:** AC-007. |

### 12.5 Question Bank and Coverage Requirements

| Requirement ID / Name | Actor / Priority | Requirement Detail |
|---|---|---|
| FR-QB-001 - Blueprint-Based Batch Generation | Assessment Agent / Must Have | **Description:** The system shall batch-generate applicable MCQ, True/False, Numerical, Short Subjective, Long Subjective, and Python 3.11 Coding items from an assigned-Teacher-configured Topic/type/difficulty/Bloom blueprint.<br>**Pre:** ACTIVE curriculum/content and valid blueprint.<br>**Trigger:** Assigned Teacher starts generation.<br>**Input:** Blueprint, requested item count, active configured cap, Topics, and approved chunks.<br>**Processing:** Generate a versioned DRAFT QuestionBankVersion linked to exact source versions; corrected items create new Question versions.<br>**Val:** Blueprint counts are nonnegative; requested total is `1..configured_cap`; configured cap is `1..200`; readiness sufficiency is checked for planned diagnostics/quizzes.<br>**Output:** DRAFT items/version.<br>**Post:** Critic review runs.<br>**AC:** Requested mix and configured cap are enforced with no live generation. |
| FR-QB-002 - Required Item Fields | System / Must Have | **Description:** The system shall store topic, type, initial/calibrated difficulty, Bloom level, estimated time, answer key, rubric where subjective, at least three test cases where coding, distractor rationale where applicable, and source chunk references.<br>**Pre:** Generated/manual item.<br>**Trigger:** Save item.<br>**Input:** Item payload.<br>**Processing:** Type-specific schema validation.<br>**Val:** Mandatory fields by type; references must be approved and in subject scope.<br>**Output:** Valid draft item.<br>**Post:** Item eligible for critique/review.<br>**AC:** AC-008. |
| FR-QB-003 - Critic Validation | Critic Agent / Must Have | **Description:** The system shall check unambiguous correctness, distractor plausibility, syllabus alignment, scope, versioned embedding-duplicate threshold/model, and rubric completeness.<br>**Pre:** Draft items and validated similarity configuration.<br>**Trigger:** Assessment generation completion.<br>**Input:** Item, approved material, and configuration version.<br>**Processing:** Structured critique per item.<br>**Val:** Failed items are not approval-ready; a model/threshold change requires revalidation.<br>**Output:** Pass/fail, reasons, repair status, and configuration reference.<br>**Post:** Reviewable bank generated.<br>**AC:** Out-of-scope, duplicate, or incomplete-rubric items cannot enter READY bank. |
| FR-QB-004 - Sample Review and Subject Owner Approval | Subject Owner / Must Have | **Description:** The system shall select a reproducible 10% sample rounded up and stratified across Topic, type, and difficulty; any critical correctness/scope/rubric/test/source failure blocks approval until correction and a new sample review.<br>**Pre:** Critic-passed DRAFT version exists.<br>**Trigger:** Subject Owner begins/completes review.<br>**Input:** Version, sample decisions, and corrections.<br>**Processing:** Store review evidence and version state.<br>**Val:** Owner authorization, complete sample, zero unresolved critical failures.<br>**Output:** READY or RETURNED version.<br>**Post:** Only READY items are serveable; version becomes immutable.<br>**AC:** AC-009. |
| FR-QB-005 - Exposure and Item Analysis | System, Teacher / Must Have | **Description:** The system shall track exposure per exact Question version, prevent same-Student reuse within 21 days, enforce the rolling 40%-of-Section cap, and after 30 final valid responses calculate `p_value=mean(c_i)`, calibrated difficulty, and point-biserial discrimination against assessment total excluding the item.<br>**Pre:** Response/exposure data exists.<br>**Trigger:** Selection or recalibration job.<br>**Input:** Same-version final valid responses from all active sharing SubjectInstances.<br>**Processing:** Apply exposure controls and metrics; mark `p<0.15` or negative discrimination suspect.<br>**Val:** Fewer than 30 responses retain initial difficulty and no statistical suspect decision; cap rounds up.<br>**Output:** Eligibility, metrics, and suspect status.<br>**Post:** Suspect evidence is excluded and affected mastery recomputes.<br>**AC:** AC-015 and AC-026. |
| FR-COV-001 - Audited Coverage State Update | Teacher / Must Have | **Description:** The system shall allow an assigned Teacher to move a Topic forward or backward among `NOT_STARTED`, `IN_PROGRESS`, `COVERED`, and `REVISED` per SubjectInstance.<br>**Pre:** ACTIVE curriculum and assignment.<br>**Trigger:** Teacher update.<br>**Input:** Topic, new state, and backward-change confirmation.<br>**Processing:** Persist current state/history and emit replan event.<br>**Val:** Valid relationship; backward changes require confirmation.<br>**Output:** New state.<br>**Post:** Downstream reads use only the latest actual state.<br>**AC:** AC-011. |
| FR-COV-002 - Bulk Unit Update and History | Teacher / Should Have | **Description:** The system shall allow a whole unit to be marked to one coverage state and shall record `updated_by` and `updated_at` for every affected topic.<br>**Pre:** Unit belongs to assigned subject.<br>**Trigger:** Bulk update.<br>**Input:** Unit and state.<br>**Processing:** Atomic multi-topic update.<br>**Val:** Confirm affected topics; all-or-none transaction.<br>**Output:** Updated statuses and count.<br>**Post:** History is auditable.<br>**AC:** Failure on one invalid topic does not leave a partial bulk update. |
| FR-COV-003 - Prerequisite Warning | Teacher / Must Have | **Description:** The system shall warn, but not block, when a Teacher marks a Topic `COVERED` while any prerequisite is `NOT_STARTED`.<br>**Pre:** Prerequisite graph/status exists.<br>**Trigger:** Covered update.<br>**Input:** Topic/new state.<br>**Processing:** Check prerequisite states.<br>**Val:** Warning names prerequisites; Teacher may confirm.<br>**Output:** Warning and completed update.<br>**Post:** Out-of-order teaching remains allowed and logged.<br>**AC:** AC-011. |
| FR-COV-004 - Coverage Dependency and Staleness | System / Must Have | **Description:** The system shall gate checkpoints/planning from current actual coverage and create in-app Teacher/Admin notifications after seven days without an update; no projected coverage state is produced.<br>**Pre:** Active term/SubjectInstance.<br>**Trigger:** Diagnostic/planner/dashboard/nightly job.<br>**Input:** Coverage history.<br>**Processing:** Apply downstream rules and staleness detection.<br>**Val:** Never mutate or substitute actual coverage automatically.<br>**Output:** Valid scope/eligibility and persistent stale notifications.<br>**Post:** Planner continues from the last actual state.<br>**AC:** AC-012. |

### 12.6 Diagnostic and Grading Requirements

| Requirement ID / Name | Actor / Priority | Requirement Detail |
|---|---|---|
| FR-DIA-001 - Prerequisite Diagnostic | Admin / Must Have | **Description:** The system shall create one versioned prerequisite-diagnostic session for each Program/Semester/Subject offering, targeted to selected Sections and opened within the first 14 calendar days of the term, with mastery source weight `0.9`.<br>**Pre:** Relevant prerequisite Topics and a READY bank exist.<br>**Trigger:** Admin configures the session.<br>**Input:** Target Sections, up to five Topics, window, duration, supervision, and item limit.<br>**Processing:** Validate the offering, timing, shared blueprint, and capacity before scheduling.<br>**Val:** Admin only; one session version per offering; first-14-day window; at most five Topics and 40 items.<br>**Output:** Versioned PREREQ session.<br>**Post:** Eligible Students receive an in-app notification and can attempt during the window.<br>**AC:** AC-010. |
| FR-DIA-002 - Coverage Checkpoint | Teacher / Must Have | **Description:** The system shall let an assigned Teacher create a checkpoint using selected Topics whose current actual coverage is `COVERED` or `REVISED`, target Sections, open/close window, duration, supervised flag, and maximum items.<br>**Pre:** READY bank and eligible actual coverage states exist.<br>**Trigger:** Teacher creates session.<br>**Input:** Session settings.<br>**Processing:** Snapshot and validate scope and schedule.<br>**Val:** Reject every Topic outside `COVERED`/`REVISED` and name it; actor must be assigned to every targeted SubjectInstance.<br>**Output:** CHECKPOINT session with source weight `1.0` supervised or `0.8` unsupervised.<br>**Post:** Target Students receive an in-app notification and can attempt during the window.<br>**AC:** AC-010. |
| FR-DIA-003 - Adaptive Selection Loop | DiagnosticEngine / Must Have | **Description:** The system shall begin each Topic at Medium difficulty, step up after a correct response and down after an incorrect response, and select reproducibly from approved eligible items.<br>**Pre:** Active attempt and item pool.<br>**Trigger:** First/next item request.<br>**Input:** Session blueprint and current raw responses.<br>**Processing:** Deterministic CAT-lite selection using seed `(session_version_id, student_id, topic_id, bank_version_id)` and stable item ordering.<br>**Val:** Scope, approval, difficulty bounds, blueprint, and exposure rules.<br>**Output:** Next item and selection trace.<br>**Post:** Selection state updated; no final grade assigned by this service.<br>**AC:** Identical versioned inputs produce the same item sequence. |
| FR-DIA-004 - Blueprint, Capacity, and Exposure | DiagnosticEngine / Must Have | **Description:** The system shall use only MCQ, True/False, and Numerical items in adaptive diagnostics; enforce at least three items per Topic including at least one Remember/Understand and one Apply/Analyze item; prevent 21-day same-Student reuse; and enforce the rolling 40%-of-Section exposure cap.<br>**Pre:** Sufficient READY bank items.<br>**Trigger:** Session preflight and item selection.<br>**Input:** Blueprint and exposure history.<br>**Processing:** Require capacity of at least five eligible items per Topic for supervised sessions or six per Topic for unsupervised sessions, then filter and select deterministically.<br>**Val:** Three to 40 total items, at most five Topics, and `max_items >= 3 * topic_count`; no constraint is bypassed when capacity is insufficient.<br>**Output:** Preflight result and compliant item or controlled no-item result.<br>**Post:** Exposure recorded when served.<br>**AC:** An undersupplied session cannot open and names each deficient Topic. |
| FR-DIA-005 - Stop and Handoff | DiagnosticEngine / Must Have | **Description:** The system shall stop a Topic after its provisional session confidence reaches `0.60` and its blueprint is met, or stop the session when maximum items or time expires, then emit all raw responses to final common grading without assigning scores itself.<br>**Pre:** Active attempt.<br>**Trigger:** Response/clock/limit event.<br>**Input:** Selection state, raw responses, and provisional correctness returned by AutoGrader.<br>**Processing:** Compute `E_session = sum(source_weight)` for provisionally correct/incorrect auto-graded items and `C_session = E_session / (E_session + 3)`; evaluate stop conditions; close attempt; invoke final grading flow.<br>**Val:** Exactly one terminal state; provisional results are hidden and do not update mastery before submission.<br>**Output:** Raw response set and selection/stop trace.<br>**Post:** Final grading pending.<br>**AC:** AC-010. |
| FR-DIA-006 - Timed Attempt and Autosave | Student / Must Have | **Description:** The system shall provide one attempt per DiagnosticSession version, with a Teacher/Admin-configured duration from 10 to 60 minutes (default 30), three to 40 items consistent with the blueprint, autosave, and submission on manual action or expiry.<br>**Pre:** Student eligible and session open.<br>**Trigger:** Start/answer/expiry.<br>**Input:** Raw answers.<br>**Processing:** Timestamp and autosave without grading feedback during the attempt.<br>**Val:** One attempt; server time authoritative; Topic/item/duration bounds enforced.<br>**Output:** Recoverable attempt state/submission.<br>**Post:** Tutor lockdown remains active for the Student until the entire DiagnosticSession closes, even after early submission.<br>**AC:** Refresh restores the last autosaved answers; a second attempt is rejected; early submission does not end lockdown. |
| FR-GRD-001 - Common Grading Entry | System / Must Have | **Description:** The system shall route every submitted response from diagnostic, Teacher-created quiz, or Student practice to a single type-dispatched grading flow and write uniform ItemResponse fields.<br>**Pre:** Submitted raw response and approved Question version.<br>**Trigger:** Attempt submission.<br>**Input:** Source type, response, and grading artifacts.<br>**Processing:** Dispatch by item type and assign an evidence status.<br>**Val:** Unsupported or missing grading artifact fails to a reviewable state.<br>**Output:** Correctness/partial score, grader type, confidence where applicable, moderation state, misconceptions, and validity state.<br>**Post:** Only final, valid, nonsuspect evidence can reach LearnerModelService.<br>**AC:** AC-013. |
| FR-GRD-002 - MCQ and True/False | AutoGrader / Must Have | **Description:** The system shall grade MCQ and True/False using exact answer-key comparison.<br>**Pre:** Valid answer key.<br>**Trigger:** Response grading.<br>**Input:** Selected answer and key.<br>**Processing:** Deterministic equality comparison.<br>**Val:** Normalize only defined representation, not semantic guesses.<br>**Output:** `is_correct`, score 0 or 1, `graded_by=KEY`.<br>**Post:** Evidence stored.<br>**AC:** Same response/key always produces same result. |
| FR-GRD-003 - Numerical | AutoGrader / Must Have | **Description:** The system shall grade a numerical response using `abs(submitted_value - expected_value) <= absolute_tolerance`, where tolerance is stored per Question in the expected unit and defaults to `0`.<br>**Pre:** Numeric answer, expected value, expected unit if applicable, and nonnegative tolerance exist.<br>**Trigger:** Response grading.<br>**Input:** Parsed value, expected value, absolute tolerance.<br>**Processing:** Deterministic absolute-tolerance comparison without automatic unit conversion.<br>**Val:** Invalid numeric input or mismatched required unit scores incorrect with clear feedback.<br>**Output:** Correctness/score and comparison reason.<br>**Post:** Evidence stored.<br>**AC:** Values at/inside the tolerance boundary pass; values outside fail consistently. |
| FR-GRD-004 - Coding | AutoGrader, optional Grading Agent / Must Have | **Description:** The system shall execute Python 3.11 code without network in a non-privileged isolated Docker sandbox using one CPU, 256 MB memory, 10-second startup/compile limit, 5 seconds per test, 30 seconds total, and 1 MB output cap; non-timeout partial score is `passed_test_count / total_test_count`, while any timeout produces score `0`. An LLM may add non-scoring style commentary.<br>**Pre:** Python code and at least three test cases.<br>**Trigger:** Code submission.<br>**Input:** Code and equally weighted test cases.<br>**Processing:** Run, capture per-test result, and kill/clean on any limit.<br>**Val:** No host/network access and no score change from LLM commentary.<br>**Output:** Passed tests, deterministic score, timeout/error reason, optional commentary.<br>**Post:** Evidence stored.<br>**AC:** AC-014. |
| FR-GRD-005 - Subjective | Grading Agent / Must Have | **Description:** The system shall grade Short/Long Subjective answers against the approved rubric and return a normalized score in `0..1`, rationale, rubric breakdown, confidence, adapter/model version, and prompt version.<br>**Pre:** Approved rubric and response.<br>**Trigger:** Subjective submission.<br>**Input:** Answer, question, rubric, and allowed material context.<br>**Processing:** Structured LLM scoring through the configured OpenAI or Anthropic provider adapter with validation and retry-repair.<br>**Val:** Score within range, all criteria addressed, and no schema failure accepted.<br>**Output:** Proposed score and confidence.<br>**Post:** A score with confidence `>=0.7` becomes final immediately; a lower-confidence score remains pending moderation and is excluded from mastery.<br>**AC:** AC-013. |
| FR-GRD-006 - Moderation, Appeal, Override | Teacher, Student / Must Have | **Description:** The system shall queue subjective scores with confidence `<0.7`, allow a Student to appeal any formative grade, and allow an assigned Teacher to confirm or override with a mandatory reason.<br>**Pre:** A grade or pending proposed grade exists.<br>**Trigger:** Low confidence, Student appeal, or Teacher review.<br>**Input:** Grade, evidence, appeal reason, and moderation reason.<br>**Processing:** Queue and audit the review. An appealed grade becomes non-final and stops contributing to mastery until resolved.<br>**Val:** Authorized assigned Teacher; before/after values and reason are mandatory.<br>**Output:** Resolved grade and persistent in-app Student notification.<br>**Post:** Learner evidence and dependent plans are recomputed if inclusion or score changes.<br>**AC:** AC-013. |
| FR-GRD-007 - Misconceptions and Suspect Evidence | System / Must Have | **Description:** The system shall map wrong objective choices to stored distractor rationale, exclude responses to suspect Question versions from mastery, and retroactively recompute affected mastery and plans when suspect status changes.<br>**Pre:** Rationale or item-analysis status exists.<br>**Trigger:** Grading, calibration, or Learner Model run.<br>**Input:** Wrong choice, Question-version metadata, and item status.<br>**Processing:** Map tags, filter evidence, and enqueue idempotent recalculation.<br>**Val:** No invented tag without mapping and no pending/appealed/invalid/suspect evidence included.<br>**Output:** Feedback, valid evidence set, and recalculation trace.<br>**Post:** Teacher can review the suspect item and affected counts.<br>**AC:** Suspect evidence is absent from current mastery and removing suspect status reversibly restores otherwise valid evidence. |

### 12.7 Learner Model and Planner Requirements

| Requirement ID / Name | Actor / Priority | Requirement Detail |
|---|---|---|
| FR-LRN-001 - Raw Mastery | LearnerModelService / Must Have | **Description:** The system shall compute Topic raw mastery exactly as Section 23 using final valid nonsuspect responses, correctness/normalized partial score, calibrated Question-version difficulty, source weight, and recency decay.<br>**Pre:** At least one qualifying response.<br>**Trigger:** Evidence-status/score/suspect change or nightly recomputation.<br>**Input:** Topic responses and timestamps.<br>**Processing:** Exact deterministic weighted ratio.<br>**Val:** Values/ranges and nonzero denominator; pending, appealed, invalid, and suspect evidence is excluded.<br>**Output:** `mastery_raw` in `0..1`.<br>**Post:** Confidence/effective mastery computed.<br>**AC:** AC-015. |
| FR-LRN-002 - Evidence, Confidence, and Effective Mastery | LearnerModelService / Must Have | **Description:** The system shall calculate `E`, `C=E/(E+3)`, prerequisite/cold-start prior, and confidence-shrunk effective mastery exactly as Section 23.<br>**Pre:** Valid evidence/topic graph.<br>**Trigger:** Raw mastery calculation.<br>**Input:** Source/recency weights and prerequisite mastery.<br>**Processing:** Deterministic formulas.<br>**Val:** Prior is mean prerequisite effective mastery; no-prerequisite prior is `0.30`.<br>**Output:** E, confidence, prior, effective mastery.<br>**Post:** TopicMastery saved.<br>**AC:** AC-015 and AC-016. |
| FR-LRN-003 - Difficulty Recalibration and Decay | LearnerModelService / Must Have | **Description:** The system shall use initial difficulty `0.3/0.6/1.0` for Easy/Medium/Hard, replace it after at least 30 final valid responses to the same exact Question version across sharing SubjectInstances with `clamp(1 - mean(c_i), 0.3, 1.0)`, and use a 21-day recency half-life.<br>**Pre:** Item-response data.<br>**Trigger:** Recalibration/mastery job.<br>**Input:** Question version, label, qualifying response count/correctness, and evidence age.<br>**Processing:** Apply fixed calibration and decay formulas.<br>**Val:** Fewer than 30 qualifying responses cannot replace the initial value.<br>**Output:** Difficulty and recency terms.<br>**Post:** Mastery uses current version-specific values.<br>**AC:** Stale evidence has half its recency weight after 21 days and calibration never combines different Question versions. |
| FR-LRN-004 - Insufficient Evidence and Cold Start | System / Must Have | **Description:** The system shall display numeric mastery only when confidence `C >= 0.35` and at least five final valid responses exist for the Student/Topic; otherwise it shall show `Building your profile` and use evidence-based cold-start planning.<br>**Pre:** Low or incomplete evidence.<br>**Trigger:** Progress display or planner run.<br>**Input:** Confidence, qualifying-response count, prerequisite diagnostic evidence, and actual coverage.<br>**Processing:** Apply display and fallback policy; order eligible cold-start Topics using prerequisite evidence first, then approved prerequisite/syllabus order.<br>**Val:** No numeric mastery before both gates are met; the policy is not based on elapsed weeks.<br>**Output:** Display state and fallback order.<br>**Post:** Student can continue building evidence.<br>**AC:** AC-016. |
| FR-LRN-005 - Separate Engagement | LearnerModelService / Must Have | **Description:** The system shall compute Engagement Score exactly as Section 24 when at least two components are available, renormalize weights across available components, label the score `Partial` when any component is missing, and expose it only to Teacher dashboards and intervention functions.<br>**Pre:** At least two behavior-component values exist.<br>**Trigger:** Nightly/event update.<br>**Input:** Attendance, plan adherence, revision consistency, and on-time quiz completion rates.<br>**Processing:** Deterministic weighted sum with renormalization.<br>**Val:** Each available rate is `0..1`; no engagement field enters mastery or planning; low-engagement alert requires all four components.<br>**Output:** EngagementScore, component availability, and completeness label.<br>**Post:** Intervention may consume a complete score.<br>**AC:** AC-017. |
| FR-PLN-001 - Planner Trigger and Inputs | StudyPlannerService / Must Have | **Description:** The system shall run nightly and after key events: mastery/evidence change, actual coverage change, preference/availability/blackout change, exam/timetable change, SubjectInstance pin change, missed slot, or plan completion.<br>**Pre:** Student enrollment/preferences and active curriculum.<br>**Trigger:** Scheduled or debounced qualifying event.<br>**Input:** Approved graph, actual coverage, mastery/confidence, exact SubjectInstance exam dates, recurring Section timetable, institution-timezone availability/blackouts, pins, and pending/missed work.<br>**Processing:** Snapshot inputs and start an idempotent deterministic plan version.<br>**Val:** Do not accept Engagement Score and coalesce duplicate events.<br>**Output:** Versioned plan run.<br>**Post:** Steps FR-PLN-002..008 execute.<br>**AC:** AC-017 confirms engagement independence. |
| FR-PLN-002 - Topic Eligibility | StudyPlannerService / Must Have | **Description:** The system shall exclude `Core Lab` Subject Topics from adaptive planning, then mark a remaining Topic eligible exactly when current actual coverage is `COVERED` or `REVISED`, or is `IN_PROGRESS` and all prerequisites have `mastery_effective >= 0.6`.<br>**Pre:** Actual coverage and prerequisite mastery available.<br>**Trigger:** Plan run.<br>**Input:** Subject type, actual Topic state, and prerequisites.<br>**Processing:** Apply lab-scope filter and Boolean predicate without projected coverage.<br>**Val:** Unknown state is ineligible and logged.<br>**Output:** Eligible theory Topic set.<br>**Post:** Only eligible Topics are scored.<br>**AC:** AC-018. |
| FR-PLN-003 - Priority Score | StudyPlannerService / Must Have | **Description:** The system shall calculate `P(t)` using the exact weights and term definitions in Section 25.<br>**Pre:** Eligible topics and term inputs.<br>**Trigger:** Eligibility complete.<br>**Input:** Effective mastery, normalized exam weight/urgency/criticality/decay risk, Teacher pin.<br>**Processing:** Weighted sum.<br>**Val:** Normalized terms `0..1`; no engagement input.<br>**Output:** Priority and contribution explanation.<br>**Post:** Topics can be ranked.<br>**AC:** AC-019. |
| FR-PLN-004 - Prerequisite Ordering | StudyPlannerService / Must Have | **Description:** The system shall produce a deterministic priority-aware topological order: prerequisites always precede dependents, while currently available nodes use tie-break `(priority descending, deadline ascending, subject_id, topic_id)`; an unexpected cycle causes logged fallback to approved syllabus order.<br>**Pre:** Approved/fallback graph.<br>**Trigger:** Ranking complete.<br>**Input:** Eligible Topic graph, priority, and deadlines.<br>**Processing:** Stable Kahn-style topological sort with runtime cycle detection.<br>**Val:** Prerequisites precede dependents except explicit fallback ordering.<br>**Output:** Ordered candidates and optional incident.<br>**Post:** Feasibility proceeds.<br>**AC:** Repeated identical runs give identical order; a cycle produces a usable plan and incident, not a crash. |
| FR-PLN-005 - Combined Deadline-Aware Feasibility | StudyPlannerService / Must Have | **Description:** The system shall compute cumulative required and available hours at every exact SubjectInstance exam deadline before packing any slot, across one combined Student plan.<br>**Pre:** Eligible order and scheduling horizon.<br>**Trigger:** Plan run.<br>**Input:** Topic effort, revision demand, exact exam dates, 30-minute availability blocks, holidays, blackouts, and recurring Section class/lab timetable.<br>**Processing:** Intersect and subtract calendars in the institution timezone and count each shared free block once across all subjects.<br>**Val:** No negative, overlapping, or double-counted capacity; required revisions consume capacity.<br>**Output:** Per-deadline and total feasibility results.<br>**Post:** Normal or triage packing selected.<br>**AC:** AC-020. |
| FR-PLN-006 - Coverage Deficit and Triage | StudyPlannerService / Must Have | **Description:** The system shall, when any cumulative deadline is infeasible, create one Student-level CoverageDeficit with per-subject/per-deadline breakdown, switch to labeled `TRIAGE`, schedule by deterministic priority until full, and explicitly list every unscheduled eligible Topic.<br>**Pre:** Infeasible result.<br>**Trigger:** Feasibility comparison.<br>**Input:** Totals and ordered candidates.<br>**Processing:** Persist deficit and triage selection.<br>**Val:** No Topic silently omitted; `unscheduled_topic_ids` means capacity omission, not deletion.<br>**Output:** Deficit report plus triage plan.<br>**Post:** Student and assigned Teachers can view their authorized scope.<br>**AC:** AC-020. |
| FR-PLN-007 - Thirty-Minute Slot Packing | StudyPlannerService / Must Have | **Description:** The system shall split Topic effort into 30-minute blocks and greedily pack the combined plan while respecting prerequisites, deadlines, recurring timetable, availability, preferred time-of-day, and a maximum of three distinct Topics per day.<br>**Pre:** Normal/triage candidates and free blocks.<br>**Trigger:** Feasibility decision.<br>**Input:** Candidate effort, approved resources, learning preference, and blocks.<br>**Processing:** Deterministic packing; choose activity by preference-match among approved Topic resources, then fall back to approved practice.<br>**Val:** No overlap, blackout, holiday, class/lab conflict, or fourth distinct daily Topic.<br>**Output:** Daily/weekly PlanSlots with resource/activity references.<br>**Post:** Revision and explanations added.<br>**AC:** AC-021. |
| FR-PLN-008 - Revision and Explainable Output | StudyPlannerService / Must Have | **Description:** The system shall create one 30-minute revision block at 1, 3, 7, and 21 days after a Topic first crosses mastery `0.7`; revisions consume feasibility capacity and missed revisions remain pending for later runs.<br>**Pre:** First-crossing event or packed plan.<br>**Trigger:** Plan generation.<br>**Input:** Mastery crossing, priority contributions, deadlines, and free blocks.<br>**Processing:** Pack revisions by deadline and compose factual reasons for every slot.<br>**Val:** Reasons match actual inputs; revision blocks obey all calendar constraints.<br>**Output:** Complete combined StudyPlan, optional deficit, and explanations.<br>**Post:** Current version available to Student and assigned Teachers.<br>**AC:** AC-021. |

### 12.8 Daily Learning, Tutor, Recommendation, Intervention, and Reports

| Requirement ID / Name | Actor / Priority | Requirement Detail |
|---|---|---|
| FR-DAY-001 - Daily and Weekly Learning | Student / Must Have | **Description:** The system shall present current plan slots, activity type, duration, revision flag, reason, and approved resource links and record completion/missed status.<br>**Pre:** Plan exists.<br>**Trigger:** Student opens/completes activity.<br>**Input:** PlanSlot/status.<br>**Processing:** Load/display and record event.<br>**Val:** Own plan only; completion cannot modify planned topic/duration.<br>**Output:** Learning view and adherence event.<br>**Post:** Engagement/intervention may consume behavior event.<br>**AC:** AC-021. |
| FR-PRC-001 - Student Practice | Student, System / Must Have | **Description:** The system shall let a Student start unlimited eligible practice by choosing a Topic and difficulty or accepting a suggested weak Topic, using only the active READY bank.<br>**Pre:** Student enrolled, Topic eligible, and items available.<br>**Trigger:** Student starts practice.<br>**Input:** Chosen/suggested Topic and difficulty.<br>**Processing:** Filter by Subject, Topic, difficulty, exact Question version, and exposure rules; never generate live.<br>**Val:** Approval, enrollment, eligibility, and exposure constraints.<br>**Output:** Practice attempt items.<br>**Post:** Submission uses FR-GRD-001.<br>**AC:** No draft, superseded, suspect, or recently exposed item is served. |
| FR-PRC-002 - Learning Update Chain | System / Must Have | **Description:** The system shall pass practice and quiz submissions through grading, learner-model update, and an event-triggered planner recalculation when eligible evidence changes.<br>**Pre:** Submitted attempt.<br>**Trigger:** Grading or moderation completion.<br>**Input:** Graded responses.<br>**Processing:** Orchestrate `Grading -> LearnerModel -> Planner event` without changing deterministic results.<br>**Val:** Idempotent event handling and evidence-status enforcement.<br>**Output:** Feedback, updated display/mastery state, and possible new plan version.<br>**Post:** Results visible to Student.<br>**AC:** Duplicate completion events do not duplicate evidence or plan runs. |
| FR-PRC-003 - Teacher-Created Quiz | Teacher / Must Have | **Description:** The system shall let an assigned Teacher configure a one-attempt quiz for selected target Sections and Topics using a question-type/difficulty/Bloom blueprint, item count, open/close window, and duration.<br>**Pre:** Active READY bank with sufficient capacity.<br>**Trigger:** Teacher creates and publishes quiz.<br>**Input:** Target Sections, Topics, blueprint/count, window, and duration.<br>**Processing:** Preflight capacity, snapshot the bank version, select items reproducibly, and notify target Students.<br>**Val:** Teacher assigned to all targets; Topics belong to the shared Subject; no live generation; one attempt per Student/quiz version.<br>**Output:** Scheduled quiz and attempts.<br>**Post:** Tutor remains concept-only for each target Student until the entire quiz session closes.<br>**AC:** Insufficient capacity blocks publication with a per-blueprint explanation. |
| FR-TUT-001 - Approved-Material RAG | Tutor Agent / Must Have | **Description:** The system shall retrieve only approved uploaded-content chunks for the Student's enrolled Subject and answer with resolvable file/page/section citations; approved HTTPS resource links are recommendations only and are never crawled or used as RAG evidence.<br>**Pre:** Student enrolled and approved chunks exist.<br>**Trigger:** Student asks a question.<br>**Input:** Subject and question.<br>**Processing:** Subject/version/approval-filtered retrieval and grounded generation.<br>**Val:** Citation references must resolve; prompt/output logged.<br>**Output:** Cited answer.<br>**Post:** Tutor interaction retained under the privacy policy.<br>**AC:** AC-022. |
| FR-TUT-002 - Grounding Refusal | Tutor Agent / Must Have | **Description:** The system shall, when no approved retrieved chunk reaches the active versioned grounded-answer threshold (initially cosine similarity `0.70`), state that the answer is not in the course materials and advise asking the Teacher rather than use general knowledge.<br>**Pre:** Subject-filtered retrieval completed.<br>**Trigger:** Tutor query.<br>**Input:** Retrieval result and active threshold/embedding-model configuration.<br>**Processing:** Apply the compatible versioned gate.<br>**Val:** No unsupported answer/citation; threshold changes require revalidation against the named embedding-model version.<br>**Output:** Standard refusal.<br>**Post:** No unsupported academic claim added.<br>**AC:** AC-022. |
| FR-TUT-003 - Assessment Lockdown and Outage Fallback | Tutor Agent, System / Must Have | **Description:** The system shall remain in concept-only mode for a target Student until the entire active diagnostic or quiz session closes and block any query reaching the active versioned similarity threshold to an assessment Question (initially `0.85`); during LLM outage it shall provide keyword search over approved uploaded chunks.<br>**Pre:** Open assessment session or LLM unavailable.<br>**Trigger:** Tutor request.<br>**Input:** Session state, query, active Question versions, threshold/model configuration, and system health.<br>**Processing:** Session/similarity guard or deterministic search fallback.<br>**Val:** Early submission does not end lockdown; never reveal an active answer or close paraphrase; model/threshold changes require revalidation.<br>**Output:** Lockdown message, allowed concept help, or search results.<br>**Post:** Guard event logged.<br>**AC:** AC-023. |
| FR-REC-001 - Topic-Mapped Recommendation | Combined Recommendation + Intervention Agent / Should Have | **Description:** The system shall return at most three ranked approved uploaded resources, note sections, practice sets, or recommendation-only HTTPS links using weak Topics, learning preference, and available time, with every result mapped to `topic_id`.<br>**Pre:** Weak Topic and approved resources exist.<br>**Trigger:** Nightly or after a relevant replan.<br>**Input:** Topic weakness, preference, time, and resource metadata.<br>**Processing:** LLM-assisted ranking under a hard content/resource filter; external links are not crawled.<br>**Val:** No unapproved or out-of-Subject resource and no more than three results.<br>**Output:** Ranked recommendations with reason and estimated time.<br>**Post:** Visible to Student.<br>**AC:** AC-022. |
| FR-INT-001 - Intervention Detection | System, Combined Agent / Should Have | **Description:** The system shall detect the thresholds fixed in Section 28 for sustained low mastery, sharp performance drop, missed plans, low engagement, and prerequisite gaps and attach the exact evidence.<br>**Pre:** The decision's minimum evidence exists.<br>**Trigger:** Nightly job/event.<br>**Input:** Trends, plan events, engagement, graph/coverage.<br>**Processing:** Deterministic threshold detection with AI-generated concise narrative and seven-day same-type cooldown.<br>**Val:** Avoid mastery alerts on insufficient evidence; cite evidence.<br>**Output:** InterventionAlert.<br>**Post:** Teacher-first queue.<br>**AC:** AC-025. |
| FR-INT-002 - Teacher-First Resolution | Teacher, Student / Should Have | **Description:** The system shall show an alert to the assigned Teacher before any Student message; the Teacher may review, dismiss with reason, resolve, or send/approve a specific supportive nudge without risk labeling.<br>**Pre:** Alert exists.<br>**Trigger:** Teacher action.<br>**Input:** Alert/evidence/action/message.<br>**Processing:** Validate wording/visibility and record resolution.<br>**Val:** Student message contains no `at risk` classification; peers never see it.<br>**Output:** Teacher action and optional Student nudge.<br>**Post:** Audit/resolution timestamps stored.<br>**AC:** AC-025. |
| FR-NOT-001 - Persistent In-App Notifications | System / Must Have | **Description:** The system shall create scoped, persistent, read/unread in-app notifications for diagnostic/quiz openings, stale coverage, grade moderation/appeal decisions, plan/deficit changes, and interventions.<br>**Pre:** A configured domain event occurs.<br>**Trigger:** Event publication.<br>**Input:** Recipient scope, event type, entity reference, message, and severity.<br>**Processing:** Deduplicate by event/recipient, persist, and expose unread count.<br>**Val:** Authorization applies to both notification and linked entity; no email or SMS is required.<br>**Output:** Notification record.<br>**Post:** Recipient may mark it read without deleting the audit event.<br>**AC:** Replayed events do not duplicate notifications. |
| FR-RPT-001 - Role Dashboards | Student, Teacher, Admin / Should Have | **Description:** The system shall provide role-specific dashboards from scoped current data and daily historical snapshots.<br>**Pre:** User authenticated.<br>**Trigger:** Dashboard view.<br>**Input:** Role, scope, date, and filters.<br>**Processing:** Query/aggregate authorized data; class/batch/department mastery uses confidence-weighted means, excludes insufficient-evidence Students, and shows included/excluded counts plus confidence bands.<br>**Val:** Aggregates for groups smaller than five are suppressed, while authorized row-level records remain accessible.<br>**Output:** Current or historical role dashboard.<br>**Post:** None.<br>**AC:** AC-024. |
| FR-RPT-002 - Academic Reports and Export | Teacher, Admin / Should Have | **Description:** The system shall produce Coverage, Performance, Mastery, and Attendance reports from daily immutable snapshots and current data, and export authorized results to PDF and Excel.<br>**Pre:** Authorized scope and data.<br>**Trigger:** Generate/export.<br>**Input:** Date/filter/report type.<br>**Processing:** Aggregate, render, and label insufficient evidence, partial engagement, suppressed small groups, and fallback data.<br>**Val:** Export matches on-screen results and applies the same group-size/privacy rules.<br>**Output:** Report/download.<br>**Post:** Export logged.<br>**AC:** AC-024. |
| FR-RPT-003 - Daily Historical Snapshot | System / Should Have | **Description:** The system shall create one immutable, idempotent academic snapshot per institution-local calendar date for coverage, performance, mastery, engagement, and attendance reporting dimensions.<br>**Pre:** Institution timezone and source data exist.<br>**Trigger:** Nightly snapshot job after the local date closes.<br>**Input:** Current scoped facts and exact source-version references.<br>**Processing:** Calculate defined aggregates/counts/bands and persist date-keyed snapshot rows.<br>**Val:** Unique date/scope/metric key; rerun replaces no immutable result and instead verifies or safely completes missing rows.<br>**Output:** DailySnapshot records.<br>**Post:** Historical dashboards/reports can reproduce the dated result.<br>**AC:** AC-024. |

## 13. Admin Functional Requirements

This section is an actor-oriented implementation view; the normative detail remains in Section 12.

| Admin Capability | Requirement IDs | Expected Admin Outcome |
|---|---|---|
| Department, program, batch, semester, section creation | FR-ADM-001 | A valid department-wise academic hierarchy, including section capacity. |
| Teacher and Student account management | FR-AUTH-003 | Active accounts with correct roles and scope. |
| Teacher assignment | FR-ADM-002 | Exactly one PRIMARY Subject Owner per shared Subject offering, plus one or more PRIMARY/CO Teacher assignments on every active SubjectInstance. |
| Academic calendar and timetable | FR-ADM-007 | Term/holiday constraints, exact SubjectInstance exam dates, and recurring Section class/lab timetable in the institution timezone. |
| Subject and unit creation | FR-ADM-003 | Program-and-semester-scoped Subject catalogue and Unit weightage. |
| Subject-section and Teacher allocation | FR-ADM-004 | DRAFT SubjectInstances with PRIMARY/CO Teacher assignments. |
| Student import | FR-ADM-005 | Valid Students created with row-level error reporting. |
| Enrollment, electives, promotion, and transfer | FR-ADM-006 | Exactly one elective per required group, capacity validation, preview/confirm bulk placement changes, and preserved history. |
| Semester-start diagnostic triggering | FR-ADM-008, FR-DIA-001 | Authorized PREREQ sessions only. |
| Institution dashboards and reports | FR-ADM-009, FR-RPT-001..003 | Scoped current/daily-snapshot rollups and PDF/Excel exports. |
| Persistent notifications | FR-NOT-001 | Scoped read/unread alerts for configured academic events. |

Admin deletion shall be restricted when dependent academic/evidence records exist; those records shall be deactivated or archived instead of hard-deleted.

## 14. Three-Role Access Model

The system supports exactly three application roles: `ADMIN`, `TEACHER`, and `STUDENT`.

`PRIMARY`, `CO`, and `Subject Owner` are Teacher assignment/responsibility labels, not additional application roles.

- Admin has institution-wide setup, account, allocation, monitoring, prerequisite-diagnostic, audit, and reporting access.
- Teacher access is restricted to assigned SubjectInstances and their enrolled Students.
- Student access is restricted to the Student's own assigned academic and learning records.
- No additional application role may be created without a formally approved requirements change.

## 15. Teacher Functional Requirements

| Teacher Capability | Requirement IDs | Expected Teacher Outcome |
|---|---|---|
| Assigned workspace | FR-TCH-001 | Access only allocated subject-sections and enrolled Students. |
| Content upload and versioning | FR-CON-001..004 | Any assigned Teacher may upload a draft; the PRIMARY Subject Owner alone activates a version or rolls back. |
| Curriculum review and topic editing | FR-CUR-001..003 | Correct topics, outcomes, Bloom levels, time, classification, order, and prerequisite edges. |
| Topic graph approval or rejection | FR-CUR-004 | PRIMARY Subject Owner activates the shared graph; CO Teachers may perform all other review/edit work. |
| Question-bank review and approval | FR-QB-001..004 | PRIMARY Subject Owner activates the READY bank after the 10% stratified sample passes. |
| Question quality review | FR-QB-005, FR-GRD-007 | Suspect-item list from exposure/p-value/discrimination analysis. |
| Coverage Tracker | FR-COV-001..004 | Current topic state, bulk unit update, warnings, and auditable timestamps. |
| Attendance entry | FR-TCH-003 | Auditable PRESENT/ABSENT records for the assigned SubjectInstance and class date. |
| Coverage Checkpoint Diagnostic | FR-DIA-002..006 | Session limited to current `COVERED` or `REVISED` Topics in assigned sections. |
| Teacher-created quiz | FR-PRC-003 | One-attempt Section quiz with Topic/blueprint/count/window/duration configuration. |
| Grade moderation and overrides | FR-GRD-005..007 | Resolve low-confidence grades with recorded rationale. |
| Student appeal review | FR-GRD-006 | Teacher-reviewed outcome and Student notification. |
| Planner pin and deficit view | FR-TCH-002, FR-PLN-006 | Academic emphasis signal and visibility of unscheduled work. |
| Intervention handling | FR-INT-001..002 | Review evidence before a supportive Student message. |
| Analytics and reports | FR-RPT-001..002 | Heatmap, coverage progress, item flags, moderation, interventions, and exports. |

## 16. Student Functional Requirements

| Student Capability | Requirement IDs | Expected Student Outcome |
|---|---|---|
| Login | FR-AUTH-001 | Secure access to own workspace. |
| Assigned subjects | FR-STU-001, FR-ADM-006 | Read-only subjects with no selection/add/drop. |
| Availability, preferred time, blackouts, learning preference | FR-STU-002 | Recurring 30-minute availability grid in the Admin-set institution timezone, without editing official dates/timetable. |
| Take diagnostics | FR-STU-003, FR-DIA-006 | Attempt only sessions triggered and opened by authorized staff. |
| Daily and weekly plan | FR-STU-004, FR-DAY-001 | Slots, durations, revisions, reasons, and completion status. |
| Approved course materials | FR-STU-004, FR-DAY-001 | Access material connected to assigned plan/topic. |
| RAG Tutor | FR-TUT-001..003 | Cited, course-grounded help subject to lockdown/refusal. |
| Practice and quizzes | FR-PRC-001..003 | Unlimited eligible practice plus one-attempt Teacher-created quizzes, using approved items and one grading/evidence chain. |
| Feedback and mastery | FR-STU-005 | Misconception feedback and numeric mastery only with sufficient confidence. |
| Recommendations | FR-STU-006, FR-REC-001 | Ranked approved resources suited to weak topics, preference, and time. |
| Supportive interventions | FR-STU-006, FR-INT-002 | Specific learning nudge without a risk label. |
| Coverage Deficit | FR-STU-006, FR-PLN-006 | Required/available hours and all topics not scheduled because of time. |
| Appeal formative grades | FR-STU-006, FR-GRD-006 | Any formative grade may be appealed; it is excluded from mastery until an audited Teacher decision. |
| In-app notifications | FR-NOT-001 | Persistent read/unread notices linked to authorized academic records. |

Students shall never see peers' attempts, mastery, engagement, alerts, or grades.

## 17. Content Ingestion Requirements

| Area | Requirement |
|---|---|
| Supported educational content | PDF, PPTX, DOCX, and UTF-8 TXT files up to 25 MB for syllabus, unit notes, previous question papers, and lab manuals. HTTPS reference links are stored as references and are not crawled. Legacy DOC/PPT, executable files, and direct image uploads are rejected; scanned pages shall be supplied as PDF. |
| Upload | Any Teacher assigned to a SubjectInstance selects the shared Subject/unit/type and uploads a file or adds a recommendation-only HTTPS link. The system creates a new DRAFT version and queues file ingestion. |
| Validation | Validate authorization, non-empty file/link, supported type/size, and basic file readability. **Recommendation:** malware scanning is Future Scope for the student build unless a lightweight scanner is readily available. |
| OCR | Detect pages without usable text and apply OCR fallback to scanned content. OCR failure shall identify the affected asset/page rather than create empty chunks. |
| Cleaning | Remove repeated headers/footers and extraction noise while retaining page/source boundaries. Cleaning shall not silently rewrite academic meaning. |
| Chunking | Create chunks of up to 800 embedding-model tokens with 120-token overlap, without crossing a known Unit boundary; retain page association. A final shorter chunk is allowed. |
| Embedding | Generate embeddings using the configured HuggingFace embedding model and store them in pgvector. Model/version shall be recorded. |
| Metadata | Each file chunk stores `subject_id`, `unit_no`, `source_file`, `page_no` or section locator, and `chunk_type`. An external resource stores only its URL and Teacher-authored Topic/title metadata; the URL is never converted into chunks. |
| Storage | Original files go to MinIO; structured asset/chunk records to PostgreSQL; vectors to pgvector. |
| Versioning | Upload never overwrites. Approved/active content is immutable; an edit creates a new DRAFT linked to the same logical asset, while the old active chain remains usable until replacement activation. |
| Activation, link approval, and rollback | Only the PRIMARY Subject Owner may activate a successfully ingested version, approve a recommendation-only link, or reactivate a prior valid version. Existing Questions, citations, and agent runs retain exact original version references. |
| Source traceability | Every AI-generated topic/question/tutor response shall link back to the source chunk(s), file, and page/locator. |
| Failure behavior | The job is idempotent, retryable, resumable, and reports its failed stage. It shall not expose a partially ingested asset as approved content. |

PRIMARY Subject Owner activation of a successfully ingested content version constitutes approval for Tutor and Recommendation use. Other assigned PRIMARY/CO Teachers may upload and review but cannot activate or roll back content.

## 18. Curriculum Agent Requirements

| Input/Output Area | Requirement |
|---|---|
| Input | Ingested syllabus chunks plus the subject's unit structure. Non-syllabus resources may support review but shall not replace the syllabus as the extraction authority. |
| Unit extraction | Preserve or derive the syllabus units and associate every generated Topic with exactly one Unit. |
| Topic generation | Generate concise Topics in a versioned shared Subject curriculum. Downstream evidence keeps its exact curriculum/Topic-version reference; merge/split mappings must be retained. |
| Learning outcomes | Generate one or more assessable outcomes per Topic. |
| Bloom level | Assign a valid level from Remember, Understand, Apply, Analyze, Evaluate, Create. |
| Estimated study time | Assign positive `est_hours`, editable by Teacher. No default limits are defined in this specification. |
| Exam weightage | Inherit from the Topic's Unit; do not invent a separate topic exam weight unless the Teacher edits the source Unit. |
| Prerequisites | Generate intra-subject and earlier-semester cross-subject edges. Each edge includes confidence in `0..1`. |
| Confidence | Represents extraction confidence for an edge and is used when resolving cycles; it is not Student mastery confidence. |
| Cycle detection | DFS detects cycles. For each detected cycle, sort its lowest-confidence tied edges by normalized `(topic_id, prereq_topic_id)` ascending, drop the first edge, flag it, and notify the Teacher. Repeat until acyclic. |
| Orphan detection | Flag any Topic without a Unit and prevent approval until assigned or removed. |
| Duplicate detection | Merge/flag Topic pairs above the active versioned similarity threshold (initially `0.92`), retaining mappings and requiring Teacher visibility; an embedding-model or threshold change requires validation and a new configuration version. |
| Teacher review | Teacher may rename, merge, split, reorder, classify Core/Optional/Self-study, adjust hours, and add/delete edges. Validation reruns after structural edits. |
| Teacher approval | Other assigned PRIMARY/CO Teachers may complete all review/edit actions, but only the designated PRIMARY Subject Owner may approve and activate the shared curriculum. Approval is blocking. |
| Replacement/fallback | The prior active curriculum remains operational while a replacement is DRAFT. If no prior active version exists and the graph is rejected/unusable, the Subject Owner may activate a recorded flat syllabus-unit-order fallback with no cross-topic prerequisites. |
| AI control | Use a versioned prompt, strict Pydantic output, retry-with-repair, token budget, and full `agent_runs` input/output log. |

## 19. Question Bank Requirements

### 19.1 Supported Item Types and Required Artifacts

| Type | Deterministic/AI Grading Artifact | Additional Requirement |
|---|---|---|
| MCQ | Single approved answer key | Plausible distractors and `distractor_rationale`; Critic confirms a single unambiguous correct answer. |
| True/False | Boolean answer key | Statement must be unambiguous and syllabus-aligned. |
| Numerical | Expected value, expected unit where applicable, and nonnegative absolute tolerance | Pass when `abs(submitted - expected) <= tolerance`; default tolerance `0`; no automatic unit conversion. |
| Short Subjective | Teacher-approved rubric | Rubric criteria and score ranges must support partial credit. |
| Long Subjective | Teacher-approved detailed rubric | Rubric breakdown must cover all scored dimensions and total. |
| Coding | At least three deterministic test cases | Supported language, inputs/expected outputs, resource limits, and optional non-scoring style guidance. |

Every Question stores Topic, type, `difficulty_initial`, `difficulty_calibrated`, Bloom level, estimated time in seconds, applicable answer/rubric/test cases/rationale, approval status, source chunk references, exposure count, p-value, and discrimination index.

### 19.2 Generation and Quality Workflow

1. An assigned Teacher configures a generation blueprint across Topic, type, difficulty, and Bloom plus an item count; the configured project cap may be lower but shall never exceed 200 items per generation batch.
2. Generation results are cached; no item is generated on demand during a live assessment.
3. Critic Agent checks single-answer correctness, distractor plausibility, syllabus alignment, out-of-scope content, embedding duplicates, and rubric completeness.
4. Failed/schema-invalid items are repaired/retried or returned as failed; they cannot proceed silently.
5. The system selects a reproducible 10% sample, rounded up, stratified across Topic, type, and difficulty. An assigned Teacher reviews it and may edit/reject any item.
6. A critical sample failure (wrong/ambiguous key, out-of-syllabus content, missing/invalid rubric or tests, or unresolved duplicate) blocks approval until the affected items are corrected and a new sample passes. Only the PRIMARY Subject Owner may change the shared bank version to `READY`.
7. Serving queries select approved READY items only and apply Topic/difficulty/Bloom/session/exposure constraints.
8. A Question is not served to the same Student within 21 days and is served to no more than 40% of an enrolled Section in a rolling 21-day period, rounded up to a whole Student.
9. After at least 30 final valid responses to the same exact Question version across SubjectInstances sharing the Subject, calculate `p_value=mean(c_i)` and `difficulty_calibrated=clamp(1-p_value, 0.3, 1.0)`; otherwise retain initial difficulty.
10. At the same threshold calculate point-biserial discrimination against each response's assessment total excluding that item: group `correct` means normalized score `c_i=1` and `not_correct` means `c_i<1`; `r_pb = ((M_correct - M_not_correct) / SD_total_excluding_item) * sqrt(q * (1-q))`, where `q` is the fully-correct proportion and population standard deviation is used over qualifying responses. If either group is empty or the standard deviation is zero, discrimination is `UNAVAILABLE` and cannot alone mark the item suspect. Versions with `p_value < 0.15` or available `r_pb < 0` are suspect; current/prior affected mastery is recomputed without their evidence.
11. A READY bank is immutable. Edits create a replacement DRAFT bank/Question version; the old active version remains usable until the Subject Owner activates the replacement.

**Phase 3 Recommended Project Demo Target:** generate 200 items for one subject, demonstrate duplicate rate under 3%, confirm every subjective item has a rubric, and every coding item has at least three test cases. This is an acceptance/demo target, not a production SLA.

## 20. Coverage Tracker Requirements

### 20.1 States

| State | Meaning for this project |
|---|---|
| `NOT_STARTED` | Teaching of the Topic has not begun for this SubjectInstance. |
| `IN_PROGRESS` | Teaching has begun but the Teacher has not marked it fully covered. |
| `COVERED` | The Teacher confirms the Topic has been taught; it may be selected for checkpoint diagnostics. |
| `REVISED` | The covered Topic has also been revised; it remains eligible for checkpoint diagnostics and planning. |

### 20.2 Required Behavior

- Status is maintained per SubjectInstance (subject-section), not globally per Subject.
- An assigned Teacher may move a single Topic forward or backward after a class, or apply one state to a complete Unit. A backward move requires explicit confirmation.
- Each change records Topic, SubjectInstance, state, `updated_by`, and `updated_at`; bulk updates remain individually traceable.
- If a Teacher marks `COVERED` while a prerequisite is `NOT_STARTED`, the system warns and names it but allows the update.
- Coverage Checkpoint selection is limited to current actual `COVERED` or `REVISED` Topics.
- Planner eligibility follows Section 25: `COVERED`, `REVISED`, or prerequisite-ready `IN_PROGRESS`.
- Coverage dashboards show actual Teacher-entered state only; the system does not infer or display projected coverage.
- After seven days without an update, persistent in-app notifications go to assigned Teachers and Admin. Planning continues from the last actual state.
- Every coverage change, including a backward move, immediately queues plan regeneration for affected Students and retains a before/after audit record.

## 21. Diagnostic Requirements

### 21.1 A. Prerequisite Diagnostic

| Property | Requirement |
|---|---|
| Triggered by | Admin only. |
| When | One versioned session per Program/Semester/Subject offering, opened within the first 14 calendar days of the term. |
| Topic scope | Relevant prerequisite Topics from earlier semesters. |
| Purpose | Identify entry-level gaps before teaching begins. |
| Duration | Authorized creator selects 10-60 minutes; default is 30 minutes. |
| Topics and questions | Select at most five Topics and 3-40 total items; `max_items >= 3 * selected_topic_count`. Preflight requires at least five eligible items per Topic when supervised and six when unsupervised. |
| Supervision | Creator must record supervised/unsupervised; default is supervised. This flag is informational for Prerequisite Diagnostics and source weight remains `0.9`. |
| Adaptive selection | Medium starting difficulty; correct steps up; incorrect steps down; blueprint and exposure controls apply. |
| Stop conditions | Per-topic provisional session confidence at least `0.60` after blueprint completion, configured maximum items, or time expiry. |
| Student authority | Student may take an opened assigned session but cannot trigger it. |

### 21.2 B. Coverage Checkpoint Diagnostic

| Property | Requirement |
|---|---|
| Triggered by | Assigned Subject Teacher only. |
| When | After actual classroom coverage, at Teacher-selected time/window. |
| Topic scope | Teacher selects only Topics currently marked `COVERED` or `REVISED` for each targeted SubjectInstance. Any other state is rejected and named. |
| Purpose | Measure retention of material actually taught. |
| Duration | Teacher selects 10-60 minutes; default is 30 minutes. |
| Topics and questions | Select at most five Topics and 3-40 total items; `max_items >= 3 * selected_topic_count`. Preflight requires at least five eligible items per Topic when supervised and six when unsupervised. |
| Supervision | Teacher records supervised/unsupervised. Mastery source weight is `1.0` supervised and `0.8` unsupervised. |
| Adaptive selection | Same deterministic CAT-lite loop, blueprint, and exposure rules. |
| Stop conditions | Same confidence/item/time conditions. |
| Student authority | Student may take an opened assigned session but cannot create/trigger it. |

### 21.3 Deterministic DiagnosticEngine

1. Filter to active READY MCQ, True/False, and Numerical Question versions within the session Topic scope. Subjective and Coding Questions remain available for practice and quizzes but are excluded from adaptive diagnostics.
2. Filter any Question served to that Student within 21 days and enforce the 40%-of-Section rolling 21-day cap.
3. Before opening, verify the per-Topic capacity and total-item rules. Do not weaken blueprint or exposure constraints when a pool is short.
4. Begin each Topic at Medium difficulty and select deterministically with seed `(session_version_id, student_id, topic_id, bank_version_id)` plus stable Question-version ordering.
5. Enforce at least three items per Topic: at least one Remember/Understand item, at least one Apply/Analyze item, and a third eligible item.
6. After each response, call the common AutoGrader as a separate stateless service to obtain provisional correctness. Do not display or persist this provisional result as final evidence. DiagnosticEngine steps up on correct and down on incorrect but contains no answer-comparison logic.
7. For stop control, compute `E_session = sum(source_weight)` over the Topic's provisional auto-graded responses and `C_session = E_session / (E_session + 3)`. Stop that Topic when `C_session >= 0.60` and its blueprint is complete, or stop the session at maximum items/time expiry.
8. Emit and retain raw responses, selection trace, and stop reason.
9. Hand the complete raw response set to the common grading flow for final grading and persistence. DiagnosticEngine does not calculate final scores, partial credit, mastery, or engagement. Tutor lockdown remains active until the whole session closes, not merely until one Student submits.

## 22. Grading Requirements

| Item Type | Required Method | Partial Credit | Confidence / Human Control |
|---|---|---|---|
| MCQ / True-False | Exact answer-key comparison by AutoGrader | No unless a future item schema explicitly supports multi-part answers | No LLM; deterministic result. |
| Numerical | Per-Question absolute tolerance comparison by AutoGrader | No additional partial scheme; pass/fail at the tolerance boundary | No LLM; default tolerance is `0`, in the expected unit, with no automatic conversion. |
| Coding | Isolated Python 3.11 execution against equally weighted test cases | `passed_test_count / total_test_count` when no timeout; any timeout scores `0` | Correctness is deterministic. LLM may add style/approach commentary that cannot alter score. |
| Short Subjective | Rubric-driven LLM scoring | Yes, according to rubric | Return score, rationale, rubric breakdown, confidence; `<0.7` queues Teacher moderation. |
| Long Subjective | Rubric-driven LLM scoring | Yes, according to rubric | Same confidence/moderation rule. |

Diagnostics, Teacher-created quizzes, and Student practice use the same flow and store `raw_answer`, `is_correct` where meaningful, normalized `partial_score`, `time_taken_sec`, `graded_by` (`KEY|SANDBOX|LLM|TEACHER`), `grade_confidence`, evidence/moderation status, and misconception tags. Wrong-choice misconceptions are derived from stored distractor rationales, not invented after grading.

A high-confidence (`>=0.7`) AI subjective score becomes final and may contribute to mastery immediately. A lower-confidence score remains pending and excluded until Teacher moderation. A Student may appeal any formative score; an appealed score becomes non-final and is excluded until resolution. The assigned Teacher reviews the Question, grading artifact, response, rationale, confidence, and appeal reason. Confirm/override requires a reason, records old/new status and score, creates an in-app notification, and triggers recomputation. The platform does not write official university marks.

## 23. Learner Model Requirements - Mastery Score

Mastery answers: "How strong is the Student's demonstrated knowledge of this Topic, given the difficulty, trustworthiness, and age of the evidence?" It must not include attendance, study-plan completion, consistency, or submission habits.

### 23.1 Simple Explanation

1. Each graded response contributes correctness from 0 to 1, so partial credit is allowed.
2. Correctness is multiplied by difficulty. Hard correct answers contribute more; hard incorrect answers contribute zero, fixing the v1 additive-difficulty defect.
3. Evidence is weighted by source. Supervised checkpoints are strongest; self-practice is weakest.
4. Older evidence fades with a 21-day half-life so revision can return naturally.
5. Raw mastery is the weighted correctness ratio.
6. Evidence amount becomes confidence. With little evidence, confidence stays low.
7. Effective mastery is pulled toward the Topic's prerequisite prior when evidence is thin. A Topic without prerequisites uses the `0.30` cold-start prior.
8. The UI displays a precise number only after confidence reaches `0.35` and at least five final valid responses exist for that Student/Topic.

### 23.2 Exact Components

For Student `s`, Topic `t`, and all final, valid, non-appealed, nonsuspect graded ItemResponses `i`:

| Component | Symbol | Exact Value / Rule |
|---|---|---|
| Correctness | `c_i` | `0..1`; partial credit allowed for subjective/coding. |
| Calibrated difficulty | `d_i` | Easy `0.3`; Medium `0.6`; Hard `1.0`. After at least 30 final valid responses to the same exact Question version across SubjectInstances sharing the Subject, compute `p_value = mean(c_i)` and replace difficulty with `clamp(1 - p_value, 0.3, 1.0)`. |
| Source weight | `w_i` | Supervised checkpoint `1.0`; prerequisite diagnostic `0.9`; unsupervised checkpoint `0.8`; assigned quiz `0.7`; self-practice `0.4`. |
| Recency decay | `r_i` | `0.5 ^ (days_since_i / H)`, where half-life `H = 21 days`. |

### 23.3 Exact Formulas

```text
mastery_raw = SUM(c_i * d_i * w_i * r_i)
              --------------------------------
              SUM(d_i * w_i * r_i)

evidence_weight E = SUM(w_i * r_i)

confidence C = E / (E + k), where k = 3

mastery_effective = C * mastery_raw + (1 - C) * prior_t

prior_t = mean(mastery_effective of prerequisite topics of t)
          if t has prerequisites
          otherwise 0.30
```

The service shall store `mastery_raw`, `mastery_effective`, `confidence`, `evidence_weight`, `last_evidence_at`, and `updated_at`. All scores must remain in `0..1`.

For zero-evidence division, when `E=0`, `mastery_raw` is stored as null/not observed, `C=0`, and effective mastery is the defined prior. The UI uses cold-start messaging; it does not display the prior as measured mastery.

### 23.4 Insufficient Evidence

- Display numeric mastery only when `C >= 0.35` and at least five final valid responses exist; otherwise display `Building your profile`.
- Cold start is evidence-based, not tied to the first two weeks. Planning uses prerequisite-diagnostic evidence where present, then approved prerequisite/syllabus order among eligible Topics.
- Pending low-confidence, appealed, invalid, and suspect Question-version responses are excluded before calculation.
- Item suspect-status changes and Teacher moderation decisions trigger retroactive, idempotent recomputation while preserving audit history.

## 24. Engagement Score Requirements

Mastery is knowledge. Engagement is behavior. They are computed, stored, displayed, and consumed separately.

```text
engagement = 0.40 * attendance_rate
           + 0.30 * plan_adherence_rate
           + 0.20 * revision_consistency
           + 0.10 * on_time_submission_rate
```

When a subset `A` of at least two components is available, compute `engagement_partial = SUM(w_j * component_j for j in A) / SUM(w_j for j in A)`. The full formula above applies when all four are available.

| Component | Meaning | Source Status |
|---|---|---|
| Attendance rate | `PRESENT records / (PRESENT + ABSENT records)` for the Student and SubjectInstance over dated/timed Teacher-saved ClassSessions in the rolling 28 days. | A denominator of zero means this component is unavailable. |
| Plan adherence rate | PlanSlots completed by 23:59 local time on their scheduled date divided by due PlanSlots in the rolling 14 days. | Rescheduled future slots are not yet due; cancelled slots are excluded. |
| Revision consistency | Revision PlanSlots completed from one day before through one day after scheduled date divided by revision slots due in the rolling 28 days. | Outside-window completion remains learning activity but does not count as on-time revision consistency. |
| On-time submission rate | Applicable diagnostic and Teacher-created quiz attempts submitted by deadline divided by due activities in the rolling 28 days. | Student-initiated practice has no deadline and is excluded. |

Each component is normalized to `0..1`. When at least two components are available, the system renormalizes the stated weights over those components and labels the result `Partial` if any component is missing. With fewer than two components it stores `Insufficient behavioral evidence`. A low-engagement alert requires all four components to be available; partial scores may be shown to the Teacher but cannot trigger that alert. Engagement never enters Mastery Score, Topic eligibility, Planner priority, feasibility, or slot packing.

## 25. Adaptive Study Planner Requirements

The Planner answers: "Given what has actually been taught, what this Student knows, what must be learned, the academic calendar, and real available time, what should the Student study and when?" It is deterministic and explainable.

### Step 1 - Topic Eligibility

```text
eligible(t) = CoverageStatus(t) in {COVERED, REVISED}
              OR
              (CoverageStatus(t) = IN_PROGRESS
               AND mastery_effective(p) >= 0.6
                   for every prerequisite p of t)
```

`NOT_STARTED` Topics are ineligible. The current coverage is per SubjectInstance. In cold start, eligible Topics follow syllabus order until useful mastery evidence exists.

### Step 2 - Priority Score

```text
P(t) = 0.30 * (1 - mastery_effective(t))
     + 0.20 * exam_weight(t)
     + 0.20 * urgency(t)
     + 0.15 * prereq_criticality(t)
     + 0.10 * decay_risk(t)
     + 0.05 * teacher_pin(t)
```

| Term | Exact Definition | Plain-Language Interpretation |
|---|---|---|
| `1 - mastery_effective(t)` | Knowledge gap. | Lower mastery raises priority most strongly (30%). |
| `exam_weight(t)` | Unit exam weightage entered as a percentage, validated so Subject Unit weights total 100; normalized as `unit_exam_weightage / 100`. | Exam-relevant Topics receive 20%. |
| `urgency(t)` | `1 / (days_to_next_exam_covering_t + 1)`, then min-max normalized. | A nearer relevant exam raises priority without division by zero. |
| `prereq_criticality(t)` | Normalized out-degree of Topic `t` in the approved DAG. | Topics unlocking more later Topics receive 15%. |
| `decay_risk(t)` | `1 - r_last_touch` only if mastery previously exceeded `0.7`; otherwise `0`. | Previously mastered but aging knowledge receives revision pressure. |
| `teacher_pin(t)` | `1` if Teacher force-included/pinned the Topic, otherwise `0`. | Teacher direction contributes 5% but does not bypass eligibility or feasibility. |

All priority inputs used in the weighted sum shall be represented in `0..1`. Engagement Score is prohibited.

### Step 3 - Prerequisite Ordering

Use a stable priority-aware topological sort. Prerequisites always occur before dependents. Among currently available nodes, apply `(priority descending, deadline ascending, subject_id, topic_id)`. The Planner checks for cycles again and, on one, logs an incident and uses approved syllabus order instead of crashing.

### Step 4 - Feasibility Check

This step occurs before slot packing.

```text
topic_hours(t) = est_hours(t) * (1 - mastery_effective(t))
required_blocks(deadline) = CEIL((cumulative topic_hours + due revision hours) / 0.5)

available_blocks(deadline) = recurring 30-minute Student availability
                             INTERSECT institution working calendar
                             MINUS Student blackouts and holidays
                             MINUS recurring Section class/lab timetable
```

The Admin stores exact exam dates per SubjectInstance and the recurring dated/timed Section class/lab timetable in the institution timezone. Feasibility is checked cumulatively at every exact relevant exam deadline across one combined Student plan. A free block shared by multiple subjects is counted once, and each revision requires one 30-minute block. The weekly grid repeats through the horizon; the daily/weekly view may show seven days while the deficit covers the complete deadline horizon.

For normalization, urgency is min-max normalized across all eligible Topics in the Student's combined plan. If all finite urgency values are equal, each receives normalized urgency `1`; a Topic with no future exam/semester date receives `0`. Prerequisite criticality is divided by the maximum eligible out-degree; if all out-degrees are zero, all criticality values are `0`.

### Step 5 - Coverage Deficit

If any cumulative deadline requires more blocks than are available, persist one Student-level CoverageDeficit containing total required/available hours, a Subject/deadline breakdown, every unscheduled eligible Topic ID, and generation time. Surface it to the Student and each assigned Teacher within their authorized scope. `Unscheduled` means not fitted because of capacity, never deleted or silently forgotten.

### Step 6 - Triage Mode

Label the plan `TRIAGE` and schedule by the complete defined `P(t)` formula until available slots are exhausted, while still respecting prerequisite ordering. All topics left out appear in CoverageDeficit.

### Step 7 - Slot Packing

Greedily fill candidates by descending priority, subject to:

- approved topological/fallback order;
- Topic effort split across 30-minute blocks; a Topic may span multiple slots/days;
- preferred Student time-of-day where possible;
- no holiday, blackout, class, or lab overlap;
- maximum three distinct Topics per day to reduce context switching.

For each PlanSlot, choose an activity deterministically from approved resources mapped to the Topic: prefer a resource whose type matches the Student's learning preference and fits 30 minutes; use stable resource ordering for ties; fall back to READY-bank practice when no suitable resource exists.

### Step 8 - Revision Scheduling

When a Topic first crosses effective mastery `0.7`, insert one 30-minute revision block at 1, 3, 7, and 21 days. Revision demand is included in feasibility. A missed revision remains pending for a later run, and placement respects all calendar constraints.

### Step 9 - Plan Output

```text
{
  daily_plan,
  weekly_plan,
  revision_slots,
  deficit_report,
  explanations_per_slot
}
```

Every slot includes Subject/Topic, start, 30-minute duration, deterministic activity/resource reference, revision flag, and a factual reason such as `Low mastery + exam in 6 days + unlocks 4 later topics`. Plans are versioned and generated nightly plus after mastery/evidence, coverage, availability/preference/blackout, exam/timetable, pin, missed-slot, and plan-completion events. Duplicate events are coalesced idempotently.

## 26. RAG Tutor Requirements

| Area | Requirement |
|---|---|
| Scope | Tutor retrieves only from active Subject-Owner-approved uploaded content for the Student's enrolled Subject. External HTTPS links are recommendation-only and never crawled. Cross-subject retrieval is disallowed unless active content contains a traceable approved prerequisite reference. At least one chunk must meet the active versioned threshold, initially cosine similarity `0.70`. |
| Retrieval | Embed/search the question against approved subject chunks and provide the relevant chunks to the Tutor Agent. Retrieval filters are deterministic even though response composition uses an LLM. |
| Citation | Every academic answer includes a resolvable uploaded source file plus page or section locator. Unsupported citations invalidate the answer. |
| Outside material | If evidence is insufficient, reply: `I don't have this in your course materials - ask your teacher.` Minor wording changes are allowed but the refusal meaning must remain. |
| Assessment lockdown | From session opening until the entire diagnostic/quiz session closes for the target Student, Tutor operates in concept-only mode and blocks a query at the active versioned Question-similarity threshold, initially `0.85`. Early submission does not end lockdown. |
| Answer leakage | Do not provide an answer, worked result, code solution, or disguised equivalent for an active item. Log the guard event without penalizing or labeling the Student. |
| LLM outage | Fall back to keyword search over approved chunks with direct source links; do not fabricate a conversational answer. |
| Threshold governance | Grounding and lockdown thresholds are stored with the embedding-model version; any model or threshold change creates a new configuration version and must pass the validation set before activation. |
| Traceability | Store provider adapter, model/prompt/threshold versions, retrieved chunk IDs, output, timestamps, and guard/fallback decision in the authorized log. |

## 27. Recommendation Requirements

The combined Recommendation + Intervention Agent shall produce recommendations using:

- weak Topic IDs derived from valid learner evidence;
- the Student's learning preference (`video`, `text`, `practice-heavy`, `mixed`);
- available study time;
- approved uploaded material, READY-bank practice, or Teacher-approved recommendation-only HTTPS links associated with the enrolled Subject.

Each result identifies `topic_id`, resource type/reference, estimated time, rank, and a short factual reason. A hard filter removes unapproved, inactive-version, out-of-Subject, or time-incompatible resources. The Agent may rank an explicitly Teacher-approved HTTPS link but never crawl, summarize, or treat it as course evidence. Show at most three recommendations, regenerated nightly and after a relevant replan.

## 28. Intervention Requirements

| Detection | Required Evidence | Required Routing/Behavior |
|---|---|---|
| Sustained low mastery | `mastery_effective < 0.50` with `C >= 0.35` on two consecutive evidence-bearing recalculations at least 48 hours apart | Create Teacher alert; never infer this from `Insufficient Evidence`. |
| Sharp performance drop | Effective mastery decreases by at least `0.20` after new valid evidence while both before/after confidence are `>=0.35` | Show measured change and affected Topics to Teacher. |
| Missed study plans | At least three due non-cancelled PlanSlots missed in a rolling seven-day period | Show missed dates/Topics; message focuses on the next achievable action. |
| Low engagement | Engagement `<0.50` on two nightly calculations at least 24 hours apart, with all four component denominators nonzero | Teacher sees components; Student is not told a knowledge conclusion from behavior. |
| Prerequisite gap | Prerequisite effective mastery `<0.60` with `C >=0.35` while a dependent Topic is `IN_PROGRESS`/`COVERED` or due within seven days | Name the prerequisite and upcoming Topic. |

Routing is always `Teacher first -> Student supportive message`. Apply a seven-day cooldown for the same alert type, Student, and SubjectInstance unless severity increases. The Teacher can review evidence, resolve, dismiss with reason, or approve/edit a supportive action. Students shall receive concrete wording such as `Revise Unit 2 stack operations before Thursday`, never `at risk`, a prediction label, or a peer comparison. Alert evidence, Teacher action, notification time, and resolution time are audited.

## 29. Dashboard Requirements

### 29.1 Student Dashboard

- Read-only assigned Subjects.
- Today's Plan and next revision; weekly-plan link.
- Coverage Deficit warning and complete unscheduled Topic list where applicable.
- Recent assessment feedback and misconception guidance.
- Mastery by Topic only when `C >= 0.35` and at least five final valid responses exist; otherwise show `Building your profile`.
- Persistent read/unread notifications for quizzes/diagnostics, grade decisions, plan/deficit changes, and supportive interventions.
- Ranked approved-material recommendations and supportive intervention messages.
- No Engagement Score requirement is confirmed for Student display; it remains Teacher-facing.

### 29.2 Teacher Dashboard

- Assigned SubjectInstances and current Coverage Tracker with stale-update status.
- Topic x Student mastery heatmap with insufficient-evidence cells clearly distinct.
- Actual coverage and stale-update status; no projected coverage.
- Active/upcoming diagnostics and session results.
- Suspect-item flags, p-value/discrimination detail, and Question review link.
- Low-confidence grading/appeal moderation queue.
- Coverage Deficits and teacher-first intervention list.
- Class analytics and report/export entry points.

### 29.3 Admin Dashboard

- Setup completeness for active batches/semesters/sections/calendar.
- Student import/enrollment exceptions and SubjectInstances without assigned Teachers.
- Institution-level department and semester rollups.
- Teacher allocations and coverage update compliance/staleness.
- Department/semester/batch coverage, performance, mastery, and attendance rollups.
- Prerequisite diagnostic status.
- Batch comparison with privacy suppression and Subjects with stale actual coverage.
- Coverage compliance summary and end-semester report/export entry points.

Historical dashboard views use daily immutable snapshots. For Students `s` who pass the numeric-display gate, class/batch/department mastery is `SUM(C_s * mastery_effective_s) / SUM(C_s)`. Show included/excluded counts and confidence bands `Developing: 0.35-<0.60`, `Established: 0.60-<0.80`, and `Strong: 0.80-1.00`. Suppress the aggregate when the selected group has fewer than five Students, but retain authorized row-level access. Predictive commercial analytics are Future Scope.

## 30. Report Requirements

| Report | Users | Filters | Core Data | Export |
|---|---|---|---|---|
| Coverage Report | Teacher (assigned sections), Admin (institution) | Department, program, batch, semester, section, subject, unit, state, snapshot date | Actual Topic state, updated by/at, and staleness; no projected coverage | PDF, Excel |
| Performance Report | Teacher, Admin | Department, batch, semester, section, subject, assessment type/session, Topic, date | Attempts, scores, completion, difficulty/Bloom breakdown, valid item counts, suspect-item exclusion note | PDF, Excel |
| Mastery Report | Teacher, Admin | Department, batch, semester, section, subject, unit, Topic, confidence band, date | Raw/effective mastery for authorized academic use, confidence, evidence weight, last evidence; `Insufficient Evidence` instead of misleading number | PDF, Excel |
| Attendance Report | Teacher, Admin | Department, batch, semester, section, subject, date range | Attendance rate/records and relevant Engagement component; source clearly identified | PDF, Excel |

The report query and export apply the same RBAC, confidence-weighted aggregation, included/excluded counts, bands, and minimum-group-size-five suppression as dashboards. Daily immutable snapshots support historical dates. Exports match selected filters, snapshot/generation timestamp, and on-screen result. Attendance comes from dated/timed ClassSessions under FR-TCH-003.

## 31. Data Requirements

### 31.1 Core Academic and User Entities

| Entity | Purpose | Important Fields | Relationship |
|---|---|---|---|
| User | Authentication and role identity. | `id`, login identity, password hash, role enum (`ADMIN|TEACHER|STUDENT`), active status, `token_version`, invited/reset timestamps | Linked to exactly one supported role profile/scope; `token_version` supports immediate revocation. |
| Institute | Root college record and time authority. | `id`, name, IANA `timezone` | Has Departments; all academic time is interpreted in this timezone. |
| Department | Academic department scope. | `id`, code, name | Belongs to Institute; has Programs, with Subjects scoped through Program/Semester. |
| Program | Degree structure. | `id`, `dept_id`, name, `duration_semesters` | Belongs to Department; has Batches. |
| Batch | Cohort years. | `id`, `program_id`, `start_year`, `end_year` | Belongs to Program; has Semesters/Students. |
| Semester | Academic term instance. | `id`, `batch_id`, number, `start_date`, `end_date` | Belongs to Batch; has Sections and AcademicCalendar. |
| Section | Teaching group. | `id`, `semester_id`, name, capacity | Belongs to Semester; has SubjectInstances and Students. |
| AcademicCalendar | Official planning constraints. | `semester_id`, holidays, working days, version | One versioned calendar per Semester. |
| SectionTimetableSlot | Recurring class/lab commitment. | `section_id`, day-of-week, local start/end time, type, effective dates | Subtracted from every enrolled Student's planning availability. |
| Subject | Shared Program/Semester catalogue item. | `program_id`, `semester_no`, code, name, credits, type, `elective_group_id` | Has shared content/curriculum/banks/Units; instantiated for Sections. |
| ElectiveGroup | Admin-controlled choose-one-of-N grouping. | `id`, `program_id`, `semester_no`, name, required flag | Has candidate Subjects/capacities and exactly-one Admin allocation per eligible Student when required. |
| SubjectInstance | A Subject offered to one Section with an exact deadline. | `subject_id`, `section_id`, exact `exam_at`, status `DRAFT|ACTIVE` | Has TeacherAssignments, Enrollments, Coverage, diagnostics, and quizzes. |
| TeacherAssignment / SubjectOwnerAssignment | Instance authorization and shared-artifact ownership. | Teacher/SubjectInstance, role `PRIMARY|CO`; Subject/owner Teacher | Every active SubjectInstance has at least one assigned Teacher; each shared Subject has exactly one owner who is PRIMARY on a related instance. |
| Student | Learner academic placement. | roll number, `dept_id`, `batch_id`, current semester, `section_id` | Has Enrollments, Preference, Attempts, Mastery, Plans. |
| Enrollment | Authoritative assigned Subject and placement history. | `student_id`, `subject_instance_id`, elective group, effective dates, status, `auto_allocated=true` | Admin-created; exactly one Subject in each required elective group; never Student-created. |
| StudentPlacementHistory | Promotion/transfer audit. | Student, from/to batch/semester/section, effective date, actor, preview/operation ID | Preserves earlier enrollment and evidence references. |
| StudentPreference | Personal planning constraints/preferences. | `student_id`, recurring 30-minute availability grid, preferred time, blackout dates, learning preference, timezone snapshot | One current/versioned profile per Student. |

### 31.2 Content, Curriculum, and Assessment Entities

| Entity | Purpose | Important Fields | Relationship |
|---|---|---|---|
| ContentAsset / ContentVersion | Versioned shared uploaded course source. | Subject, type, file, version, `DRAFT|ACTIVE|SUPERSEDED`, storage key, uploader/activator | Has ContentChunks; any assigned Teacher uploads, PRIMARY Subject Owner activates/rolls back. |
| ApprovedResourceLink | Versioned recommendation-only external resource. | Subject, Topic, HTTPS URL, title/type/time, `DRAFT|APPROVED|SUPERSEDED`, uploader, Subject Owner approver | Only APPROVED links may be recommended; they are never crawled, embedded, cited by Tutor, or used as RAG evidence. |
| ContentChunk | Traceable retrieval unit. | `subject_id`, `unit_no`, source file, page, chunk type, text, vector/model version | Belongs to ContentVersion; referenced by AI outputs/Questions/Tutor. |
| CurriculumVersion / Unit / TopicVersion | Immutable shared curriculum chain. | Subject, version/status, unit/order/weightage, Topic stable key/version, outcomes, Bloom, hours, classification | One active chain per Subject; replacements remain DRAFT until Subject Owner activation. |
| TopicPrereq | Directed prerequisite relation. | `topic_id`, `prereq_topic_id`, confidence, `approved_by_teacher` | Forms approved DAG; may reference earlier-subject Topic. |
| CoverageStatus | Actual teaching progress per class. | `subject_instance_id`, `topic_id`, state, `updated_by`, `updated_at` | Gates diagnostics/planning. |
| QuestionBankVersion / QuestionVersion | Immutable shared assessment bank and item quality. | Subject/curriculum version, blueprint, item version/type/difficulty/Bloom/time, key/value/unit/tolerance/rubric/tests/rationale, source refs, status, p-value, point-biserial | One READY bank version per active Subject chain; exact Question version is served and calibrated. |
| DiagnosticSessionVersion | Configured PREREQ/CHECKPOINT session. | offering/instances, type, Topics, targets, actor, open/close, duration, supervision, max items, bank version, seed basis | Has one attempt per targeted Student/version. |
| QuizSessionVersion | Teacher-created quiz configuration. | target instances/Sections, Topics, blueprint/count, window, duration, bank version | Has one attempt per targeted Student/version. |
| StudentAttempt | One diagnostic, quiz, or practice attempt. | optional session version, Student, source type, start/submit timestamps, status | Has ItemResponses. |
| ItemResponse | Raw and graded evidence. | attempt, Question version, raw answer, correctness/score, time, grader/provider, confidence, final/appeal/validity status, misconceptions | Learner Model consumes only final valid non-appealed nonsuspect evidence. |
| ClassSession | Dated/timed class occurrence. | `subject_instance_id`, starts/ends at, type, created/recorded by | Has AttendanceRecords and prevents ambiguous date-only attendance. |
| AttendanceRecord | Manual attendance for one Student in one ClassSession. | `class_session_id`, `student_id`, `PRESENT|ABSENT`, `recorded_by`, `recorded_at` | Entered by assigned Teacher; aggregated into Engagement/Attendance Report. |

### 31.3 Learning, Planning, and Governance Entities

| Entity | Purpose | Important Fields | Relationship |
|---|---|---|---|
| TopicMastery | Current knowledge state per Student/Topic. | raw/effective mastery, confidence, evidence weight, last evidence, updated time | Derived from ItemResponses and prerequisite prior. |
| EngagementScore | Separate behavior state. | Student, SubjectInstance, score, component JSON, available count, `COMPLETE|PARTIAL|INSUFFICIENT`, updated time | Consumed only by Teacher dashboard/intervention; low-engagement alert requires COMPLETE. |
| StudyPlan | Versioned Student plan for date/horizon. | Student, date, generated time, version, mode | Has PlanSlots and optional CoverageDeficit. |
| PlanSlot | Scheduled learning activity. | plan, Subject/Topic, start, fixed 30-minute duration, activity/resource, revision flag, reason, completion state | Belongs to the combined StudyPlan. |
| CoverageDeficit | Explicit infeasibility result. | Student, totals, per-Subject/deadline breakdown, unscheduled Topic IDs, generated time | One per infeasible combined plan; visible by authorized scope. |
| InterventionAlert | Teacher-first concern record. | Student, SubjectInstance, type, severity, evidence JSON, Teacher notification, resolution | Visible to assigned Teacher; optional supportive Student message. |
| Notification | Persistent in-app delivery. | recipient, event/entity, message/severity, created/read timestamps, deduplication key | Links to an authorized record; replay does not duplicate it. |
| DailySnapshot | Immutable historical reporting state. | snapshot date/timezone, scope/entity, metric type, values/counts/bands, source-version refs | Powers dated dashboards/reports and group suppression. |
| AIProviderConfiguration / AgentRun | Provider abstraction and versioned call trace. | active OpenAI/Anthropic adapter, model/prompt/config versions; run token usage, pseudonymous input/source refs, structured output, status/timestamps | Deployment selects an adapter; external calls receive only minimized pseudonymous data. |
| AuditLog | Approval/override/change accountability. | actor, action, entity, before/after or references, reason, timestamp | Records graph/bank approvals, coverage changes, grade overrides, exports, etc. |

Data integrity requires foreign keys, scoped uniqueness, enums/check constraints, immutable approved versions, timestamps, and transactions for multi-record updates. Operational/academic data retention is configurable with a default of one academic year after term end; audit/security records default to two years. Legal hold or configured policy may extend retention. Expiry uses an audited background process and preserves required referential tombstones. Synthetic/anonymized demo data is preferred.

## 32. AI Agents

The platform uses six LLM agents by treating Recommendation + Intervention as one combined agent with two responsibilities.

| Agent | Purpose | Input | Output | Human Approval? | Trigger |
|---|---|---|---|---|---|
| Curriculum Agent | Convert syllabus into Topics, outcomes, Bloom, time, and prerequisite candidates. | Syllabus chunks, unit structure | Draft topic graph with edge confidence | Yes; PRIMARY Subject Owner activates | Batch per requested Subject/version |
| Assessment Agent | Generate a structured question bank from a Teacher blueprint. | Approved Topics/source chunks, Topic/type/difficulty/Bloom blueprint, item count up to configured maximum 200 | Draft MCQ/TF/numerical/subjective/coding Questions | Yes; PRIMARY Subject Owner activates READY bank | Batch after curriculum approval |
| Critic Agent | Critique generated items. | Draft Question plus source/rules | Structured pass/fail, issues, repair request | Teacher approval still required | Batch chained after Assessment Agent |
| Grading Agent | Rubric-grade subjective answers and optionally comment on coding style/approach. | Question, rubric, pseudonymous response, minimized approved context | Subjective score/rationale/breakdown/confidence; non-scoring code commentary | Teacher for `<0.7` or any appeal; all grades remain formative | On submission after type dispatch |
| Tutor Agent (RAG) | Answer Student doubts from approved subject material with citations. | Student query and retrieved approved chunks | Cited answer/refusal/lockdown response | No per response; sources are pre-approved and guards are mandatory | Real time |
| Recommendation + Intervention Agent | Rank approved resources and compose evidence-based Teacher alerts/supportive messages. | Weak Topics, preference, time, approved resources; mastery/engagement/plan/prerequisite evidence | Ranked recommendations; intervention narrative | Teacher first for interventions; no per-item approval specified for recommendations | Nightly/on demand as defined |

All agents use a provider-neutral interface; deployment configuration selects either the OpenAI or Anthropic adapter and named model. Calls require a versioned provider/model/prompt/configuration, strict Pydantic output schema, retry-with-repair, token budget, source references, and access-controlled trace logging. External AI providers receive minimized pseudonymous data only. AI outputs never bypass deterministic filters or Subject Owner gates.

## 33. Deterministic Services

| Service | Responsibility | Input | Processing | Output | Why Deterministic |
|---|---|---|---|---|---|
| IngestionService | Prepare uploaded sources for storage/retrieval. | Valid content version | OCR fallback, clean, semantic chunk, embed, store metadata | Stored asset/chunks/vectors and status | Reproducible pipeline and traceability; no judgment workflow. |
| DiagnosticEngine | Select/serve adaptive items. | Session scope/blueprint, response/selection state, exposure history, READY bank | Difficulty progression, blueprint, exposure controls, stop rules | Next item or raw response set/stop trace | Must be fast, auditable, and repeatable; it never grades. |
| AutoGrader | Grade objective, numerical, and coding correctness. | Raw response and key/tolerance/test cases | Exact/tolerance comparison or isolated test execution | Deterministic score/test result/reason | Correctness is not an LLM judgment. |
| LearnerModelService | Calculate mastery, evidence confidence, prior, and separate engagement. | Valid graded evidence, graph, behavior rates | Exact Sections 23-24 formulas | TopicMastery and EngagementScore | Original Algorithm #1; must be unit-testable and defensible. |
| StudyPlannerService | Build feasible adaptive plan. | Approved graph, coverage, mastery, calendar, preferences, pins, pending/missed work | Eligibility, formula, topological order, feasibility, triage, packing, revision | StudyPlan, reasons, optional CoverageDeficit | Original Algorithm #2; same inputs produce same result. |

LangGraph may coordinate batch and runtime chains, but it shall not wrap these services in LLM reasoning or alter their results.

## 34. AI vs Deterministic Responsibility Matrix

| Function | AI/LLM Responsibility | Deterministic Code Responsibility | Human Responsibility |
|---|---|---|---|
| Content ingestion | None | Validate, OCR, clean, chunk, embed, store/version | Assigned Teacher uploads; PRIMARY Subject Owner activates/rolls back |
| Curriculum | Extract draft Topics/outcomes/Bloom/time/edges | Schema checks, cycle/orphan/duplicate handling, fallback | Assigned Teachers edit/review; PRIMARY Subject Owner activates/rejects |
| Question bank | Generate Questions; Critic quality review | Type schema, reproducible 10% sample, critical-failure gate, similarity/exposure/version-specific item metrics | Assigned Teachers review/edit; PRIMARY Subject Owner activates/returns |
| Diagnostic | Optional closing narrative only | Scope validation, adaptive selection, blueprint, exposure, stop | Admin triggers prerequisite diagnostics; assigned Teacher triggers checkpoints; Student takes |
| MCQ/TF grading | None | Exact key match | Teacher may review dispute |
| Numerical grading | None | Tolerance comparison | Teacher defines/reviews tolerance |
| Coding grading | Optional non-scoring style comment | Sandbox/test-case correctness and partial credit | Teacher authors/approves tests and reviews dispute |
| Subjective grading | Rubric score/rationale/breakdown/confidence | Schema/range checks, high-confidence finalization, pending/appeal exclusion, record handling | Assigned Teacher moderates low confidence/appeals; all results remain formative |
| Mastery | None | Exact knowledge formula/confidence/prior/decay | Teacher interprets; Student builds evidence |
| Engagement | None | Exact available-component formula, renormalization, completeness label | Teacher interprets for support |
| Study planning | None | Exact eligibility/priority-aware topology/cumulative deadlines/30-minute capacity/triage/packing/revision | Teacher pins per SubjectInstance; Student supplies availability |
| Tutor | Compose grounded answer from retrieved chunks | Access/retrieval filters, citation/session/similarity guards, keyword fallback | Teacher approves sources |
| Recommendation | Rank/describe approved resources | Hard scope/approval/time filter | Student chooses resource; Teacher controls source material |
| Intervention | Draft narrative/supportive wording | Detect the fixed Section 28 thresholds and enforce cooldown/routing/visibility | Teacher reviews/resolves/messages first |
| Reporting | Optional narrative is not required | Daily snapshots, confidence-weighted aggregates, privacy suppression, filter/export | Authorized actor selects filters |

## 35. Non-Functional Requirements

| ID | Category | Requirement | Status / Target |
|---|---|---|---|
| NFR-PERF-001 | Performance | Non-AI CRUD, dashboard-summary, and plan-read requests shall remain usable under the validation dataset and authenticated concurrency target. | 95% complete within 2 seconds at 100 concurrent authenticated users, excluding file/AI jobs. |
| NFR-PERF-002 | Performance | Ingestion, curriculum generation, and bank generation shall execute as background jobs with progress/status rather than block an HTTP request. | Confirmed behavior; exact duration not specified. |
| NFR-PERF-003 | Performance | Diagnostic next-item selection and autosave shall be fast enough not to interrupt a timed attempt. | **Recommended Project Target:** selection under 1 second and autosave acknowledgment under 2 seconds in demo environment. |
| NFR-SEC-001 | Security | JWT authentication, bcrypt password hashing, and exactly three RBAC roles—`ADMIN`, `TEACHER`, and `STUDENT`—shall be implemented. | Confirmed. |
| NFR-SEC-002 | Security | Role scope shall be enforced at query as well as route layer. | Confirmed. |
| NFR-SEC-003 | Security | Python 3.11 code shall run without network in a non-privileged isolated sandbox with one CPU, 256 MB memory, 10-second startup/compile, 5 seconds per test, 30 seconds total, and 1 MB output limits. | Fixed project target. |
| NFR-REL-001 | Reliability | Long Celery tasks shall be idempotent, retryable, and resumable without duplicate final records. | Confirmed. |
| NFR-REL-002 | Reliability | LLM outage shall not stop objective grading, learner-model formulas, planner formulas, or access to already processed material. | Confirmed. |
| NFR-USE-001 | Usability | Role navigation shall expose only relevant modules; status, warnings, reasons, and failures shall use plain academic language. | Confirmed intent. |
| NFR-USE-002 | Usability | Timed Student attempts shall autosave and show remaining time; coverage updates shall be single-click with optional unit bulk action. | Confirmed. |
| NFR-USE-003 | Accessibility and Browser Support | Major Admin, Teacher, and Student flows shall meet WCAG 2.1 AA and work responsively on current stable Chrome and Edge desktop/mobile viewport sizes. | Keyboard navigation, focus, labels, contrast, zoom/reflow, and automated/manual accessibility evidence required. |
| NFR-MNT-001 | Maintainability | Deterministic services shall be pure/unit-testable functions with documented formula terms; prompts shall be outside business logic in a versioned registry. | Confirmed. |
| NFR-MNT-002 | Maintainability | Backend APIs shall provide generated OpenAPI documentation and use Pydantic schemas; database changes shall use Alembic. | Specified deliverable/baseline. |
| NFR-TST-001 | Testability | The five deterministic services shall have at least 80% automated test coverage, including boundary/failure cases. | Confirmed project target. |
| NFR-TST-002 | Testability | Each phase shall include unit/integration tests, seed/demo data, and documented acceptance evidence. | Confirmed deliverable. |
| NFR-DAT-001 | Data Integrity | IDs, foreign keys, state enums, scoped uniqueness, transactions, and timestamps shall prevent orphaned or partially updated core records. | Confirmed intent. |
| NFR-DAT-002 | Data Integrity | Content/plan/prompt/output versions and source references shall remain resolvable after a later version is activated. | Confirmed. |
| NFR-AUD-001 | Auditability | Teacher approvals, overrides, grade changes, coverage changes, and exports shall record actor/time and required reason/context. | Confirmed. |
| NFR-AUD-002 | Auditability | Diagnostic selection and plan generation shall retain input/version/decision traces sufficient to explain results. | Confirmed deterministic/auditable intent. |
| NFR-AI-001 | AI Reliability | Every LLM output shall pass strict schema/range/reference validation with retry-with-repair; invalid output shall fail safely. | Confirmed. |
| NFR-AI-002 | AI Reliability | Every LLM call shall record agent, provider adapter, versioned prompt/model/configuration, minimized pseudonymous input/output, token budget, status, and source references. | Confirmed. |
| NFR-AI-003 | AI Reliability | AI academic content shall remain draft until the specified human approval; Tutor and Recommendation output shall remain hard-filtered to approved sources. | Confirmed. |
| NFR-AI-004 | Portability | AI calls shall use a provider-neutral service interface, with deployment configuration selecting an OpenAI or Anthropic adapter without changing domain workflows or schemas. | Contract tests run against both adapters using stubs; one adapter may be active per deployment. |
| NFR-SCL-001 | Demonstration Scale | The validation dataset shall support one college, up to five Departments and 2,000 Student records. | Fixed project target. |
| NFR-SCL-002 | Assessment Concurrency | The system shall support 60 simultaneous timed diagnostic/quiz attempts within the response targets, including selection and autosave. | Load-test evidence required. |

## 36. Security Requirements

| ID | Requirement | Enforcement / Verification |
|---|---|---|
| NFR-SEC-004 | JWTs shall expire four hours after issue and no refresh tokens shall be issued. Every protected request shall verify signature/expiry, active account, and matching `token_version`; password reset, deactivation, or Admin revocation increments that version for immediate logout. | Authentication/revocation tests; user logs in again after expiry. |
| NFR-SEC-005 | Passwords shall never be stored or logged in plaintext; Passlib/bcrypt hashes shall be used. | Database/log inspection and login tests. |
| NFR-SEC-006 | Students shall access only their own profile, enrollments, plans, attempts, grades, mastery, recommendations, deficits, and supportive messages. | Query-scope tests using another Student's IDs. |
| NFR-SEC-007 | Teachers shall access learner/content/assessment data only for assigned SubjectInstances. | Assignment-scoped query tests. |
| NFR-SEC-008 | Enrollment changes shall be denied to Student role. | Student `POST/PUT/DELETE` enrollment returns `403`. |
| NFR-SEC-009 | Uploaded PDF/PPTX/DOCX/TXT files shall be checked for the 25 MB limit, readability, and declared/actual MIME mismatch; recommendation links shall use HTTPS and shall never be crawled. | Invalid-file/link and no-crawl tests; advanced malware scanning is Future Scope. |
| NFR-SEC-010 | Python 3.11 coding execution shall use an isolated Docker container with no network, non-privileged execution, read-only base, the limits in NFR-SEC-003, and cleanup. | Sandbox network/timeout/resource tests appropriate to project environment. |
| NFR-SEC-011 | Logs shall avoid passwords, tokens, and unnecessary raw personal data. External AI calls shall contain only minimized pseudonymous inputs; academic AI traces, prompts, responses, and grading evidence remain encrypted/access-controlled. | Payload/log review and unauthorized-access tests. |
| NFR-SEC-012 | Approval, moderation, appeal, grade override, graph/bank status change, and security-relevant action shall be audited. | Audit record assertions. |
| NFR-SEC-013 | Production traffic shall use TLS; secrets shall come from environment/secret management rather than source control; stored files, database backups, and sensitive AI/grade data shall be protected at rest and by least-privilege service credentials. | Deployment configuration, repository secret scan, and access tests. |
| NFR-SEC-014 | Operational/academic records shall default to retention for one academic year after term end; audit/security records default to two years. Admin-configured changes and disposal jobs shall be authorized and audited. | Retention boundary, legal-hold/configuration, and disposal tests. |
| NFR-SEC-015 | Account creation shall use single-use expiring invitation/setup tokens; password reset shall use single-use expiring tokens, invalidate earlier tokens, and revoke existing JWTs after completion. | Token expiry/replay/revocation integration tests. |
| NFR-SEC-016 | Login, invitation acceptance, password reset, Tutor, and other abuse-sensitive endpoints shall have configurable per-account and per-IP rate limits with non-enumerating error messages. | Rate-limit and account-enumeration tests. |

**Future Scope:** SSO, MFA, enterprise SIEM, managed key vault/HSM, WAF, malware-analysis service, multi-tenant isolation, and production penetration-testing program.

## 37. Error and Failure Handling

| Scenario | Expected System Behavior | User Message | Fallback |
|---|---|---|---|
| Cyclic prerequisite graph | Detect by DFS; drop/flag lowest-confidence edge before review; notify Teacher. Runtime cycle logs incident. | `A prerequisite cycle was detected. Review the flagged relationship.` | Runtime Planner uses syllabus unit order. |
| Invalid generated Question | Reject schema/quality failure, retry repair within policy, keep non-READY; expose Critic reason. | `This item needs review and will not be used.` | Teacher edits/regenerates; existing READY bank remains. |
| Tutor answer leakage | Until the entire assessment session closes, apply the active versioned similarity guard (initially `>=0.85`), do not answer, and log the guard. | `I cannot help with an active assessment question. I can explain the general concept after the assessment.` | Concept-only Tutor mode; early submission does not unlock it. |
| Student gaming quizzes | Apply source weights, randomization, time boxes, 21-day exclusion, section caps; do not accuse automatically. | No punitive label; normal session messaging. | Supervised checkpoint supplies stronger `1.0` evidence. |
| Cold start / no evidence | Use prior internally, hide numeric mastery until `C>=0.35` and five final valid responses, and order eligible Topics using diagnostic evidence then approved graph/syllabus order. | `Building your profile.` | Prerequisite Diagnostic supplies an early real signal. |
| Teacher not updating coverage | After seven days send persistent in-app notifications to assigned Teachers and Admin; do not infer projected coverage. | Teacher/Admin: `Coverage has not been updated for 7 days; planning is using the last actual state.` | Continue with the last actual state; checkpoint accepts only actual `COVERED`/`REVISED`. |
| LLM/API outage | Queue/retry batch work; do not accept invalid partial output; objective grading and deterministic services continue. | `AI service is temporarily unavailable. Your request is queued.` | Tutor keyword search over approved chunks; existing approved bank/content remains. |
| Grade dispute | Mark the formative grade `UNDER_APPEAL`, exclude it from mastery immediately, notify the assigned Teacher, and recompute affected results. | `Your appeal was submitted for teacher review.` | Teacher confirms/overrides with reason; final resolution restores the resolved evidence and triggers another recomputation. |
| Insufficient planner time | Calculate before packing; create deficit and labeled triage plan. | `Your available time cannot cover all eligible topics. Review the Coverage Deficit with your teacher.` | Prioritized triage; list every unscheduled Topic. |
| Coding timeout/infinite loop | Kill isolated process, assign score `0`, record timeout, release resources, and continue the worker. | `Execution exceeded the time limit and was scored 0.` | Teacher may review through the normal formative-grade dispute path. |
| OCR/empty extraction | Mark job failed at page/asset; do not approve empty chunks. | `Text could not be extracted from this content. Upload a clearer file or enter a reference.` | Teacher retries/replaces source. |
| Insufficient diagnostic/quiz capacity | Preflight before opening; do not generate live or violate blueprint/exposure rules; identify each deficient Topic/stratum. | `The approved bank does not have enough eligible questions for this session.` | Assigned Teacher revises the DRAFT bank/session; existing READY content remains active. |
| Partial background-job failure | Idempotently resume/retry and avoid duplicate outputs. | `Processing is incomplete and will retry. Current content is unchanged.` | Keep prior approved version active. |
| Unauthorized access | Return `403` (or non-enumerating `404` where appropriate), reveal no protected data, log event. | `You do not have permission to access this resource.` | Return to actor dashboard. |

## 38. Use Cases

### UC-001 - Configure Academic Structure and Allocation

| Field | Detail |
|---|---|
| Actor | Admin |
| Purpose | Create the authoritative structure and Student subject lists. |
| Precondition | Admin authenticated; source academic data is available. |
| Trigger | New institution/term setup. |
| Main Flow | 1. Create Department/Program/Batch/Semester/Section and institution timezone. 2. Add holidays, exact SubjectInstance exam dates, and recurring Section class/lab timetable. 3. Add Teacher accounts. 4. Create Program/Semester Subjects, Units, and elective groups. 5. Map Subjects to Sections and exactly one PRIMARY Subject Owner plus optional CO Teachers. 6. Import Students. 7. Auto-enroll core Subjects and allocate exactly one capacity-available elective per required group. 8. Admin previews/confirms exceptions. |
| Alternative Flow | Correct invalid CSV rows and re-import idempotently; preview/confirm bulk promotion or Section transfer while preserving history. |
| Exception Flow | Mismatched semester, capacity, duplicate roll/code, or missing Teacher/calendar prevents exit completion. |
| Postcondition | Every active Student has a non-empty Admin-approved read-only subject list. |

### UC-002 - Ingest Content and Approve Curriculum

| Field | Detail |
|---|---|
| Actor | Teacher; Curriculum Agent; IngestionService |
| Purpose | Establish traceable approved Topics and order. |
| Precondition | Teacher assigned; SubjectInstance exists. |
| Trigger | Teacher uploads syllabus/resources and requests generation. |
| Main Flow | 1. Any assigned Teacher creates/ingests a shared Subject DRAFT content version. 2. Subject Owner activates content. 3. Agent generates a DRAFT curriculum. 4. System checks cycle/orphan/duplicate. 5. Assigned Teachers edit/review. 6. PRIMARY Subject Owner activates it. 7. Prior active chain is superseded but remains traceable. |
| Alternative Flow | Existing active chain remains live while replacement is corrected; if none exists, Subject Owner may activate the explicit flat unit-order fallback. |
| Exception Flow | OCR/schema/validation failure remains pending/failed and cannot activate. |
| Postcondition | Approved graph or explicit fallback is available downstream. |

### UC-003 - Generate and Approve Question Bank

| Field | Detail |
|---|---|
| Actor | Teacher; Assessment Agent; Critic Agent |
| Purpose | Produce a READY, source-traceable bank. |
| Precondition | ACTIVE curriculum and approved chunks. |
| Trigger | Teacher starts batch generation. |
| Main Flow | 1. Teacher configures Topic/type/difficulty/Bloom blueprint and count up to 200. 2. Generate DRAFT items. 3. Critic validates. 4. Repair/return failures. 5. System creates reproducible 10% Topic/type/difficulty sample. 6. Teacher reviews sample/flags. 7. Critical failures cause correction and resampling. 8. PRIMARY Subject Owner activates READY bank. |
| Alternative Flow | Teacher returns bank for correction/regeneration. |
| Exception Flow | Missing rubric/tests/source or duplicate/out-of-scope item cannot become READY. |
| Postcondition | Approved items can be selected; no live generation required. |

### UC-004 - Record Topic Coverage

| Field | Detail |
|---|---|
| Actor | Teacher |
| Purpose | Record actual teaching progress used by diagnostics and planning. |
| Precondition | Assigned Teacher and ACTIVE Topics. |
| Trigger | Lecture/unit progress. |
| Main Flow | 1. Select Topic or Unit. 2. Choose any valid forward/backward state. 3. For a backward move require confirmation. 4. Check prerequisites. 5. Show any nonblocking warning. 6. Store before/after, actor/time. 7. Queue affected Student replans. |
| Alternative Flow | Bulk update entire Unit atomically. |
| Exception Flow | Unassigned Teacher, invalid Topic/state, or mismatched instance is rejected. |
| Postcondition | Current CoverageStatus is available downstream. |

### UC-005 - Run Prerequisite Diagnostic

| Field | Detail |
|---|---|
| Actor | Admin; Student; DiagnosticEngine |
| Purpose | Identify earlier-semester gaps at semester start. |
| Precondition | The Program/Semester/Subject offering is within its first 14 days; at most five prerequisite Topics and a sufficient READY bank exist. |
| Trigger | Authorized actor creates PREREQ session. |
| Main Flow | 1. Configure target Sections, up to five Topics, window, duration, supervision, and 3-40 items. 2. Preflight blueprint plus five/six-item capacity. 3. Notify Students. 4. Students start one attempt. 5. Engine uses reproducible adaptive selection. 6. Stop condition occurs. 7. Raw responses go to common grading. |
| Alternative Flow | Admin targets one or more valid Sections within the institution. |
| Exception Flow | Student trigger or invalid prerequisite scope is rejected. |
| Postcondition | Graded evidence receives source weight `0.9`. |

### UC-006 - Run Coverage Checkpoint Diagnostic

| Field | Detail |
|---|---|
| Actor | Teacher; Student; DiagnosticEngine |
| Purpose | Measure retention of actually covered material. |
| Precondition | Teacher assignment; selected Topics are currently `COVERED` or `REVISED`; READY bank and capacity exist. |
| Trigger | Teacher creates CHECKPOINT session. |
| Main Flow | 1. Select `COVERED`/`REVISED` Topics, Sections, window, duration, supervision, and max. 2. Validate every target/Topic and capacity. 3. Notify Students. 4. Students attempt. 5. Engine selects/stops deterministically. 6. Responses go to common grading. |
| Alternative Flow | Teacher removes named ineligible Topics or adjusts blueprint and retries. |
| Exception Flow | Any ineligible Topic or capacity shortfall rejects creation; no partial invalid session. |
| Postcondition | Evidence weight is `1.0` supervised or `0.8` unsupervised. |

### UC-007 - Grade an Attempt

| Field | Detail |
|---|---|
| Actor | System; Grading Agent; Teacher where required |
| Purpose | Produce consistent graded evidence from any source. |
| Precondition | Submitted raw responses and approved grading artifacts. |
| Trigger | Attempt closes/submits. |
| Main Flow | 1. Dispatch each item type. 2. Auto-grade objective/numerical/code. 3. Provider-adapter LLM grades subjective by rubric. 4. Record uniform response/evidence fields. 5. Finalize confidence `>=0.7`; queue lower confidence. 6. Send only final valid non-appealed nonsuspect evidence to Learner Model. |
| Alternative Flow | Optional non-scoring code style feedback added. |
| Exception Flow | Sandbox timeout, invalid LLM schema, or missing artifact returns controlled reason/review status. |
| Postcondition | Auditable evidence exists; no grading occurred in DiagnosticEngine. |

### UC-008 - Appeal and Moderate AI Grade

| Field | Detail |
|---|---|
| Actor | Student; Teacher |
| Purpose | Provide human review of any formative grade. |
| Precondition | Student owns a formative grade. |
| Trigger | Low confidence or Student appeal. |
| Main Flow | 1. Mark grade pending/under appeal and exclude it. 2. Recompute learner state. 3. Teacher reviews all grading evidence. 4. Confirm or override with mandatory reason. 5. Finalize and notify Student. 6. Recompute learner state and plan. |
| Alternative Flow | Teacher confirms original score with reason. |
| Exception Flow | Unassigned Teacher or another Student's grade is inaccessible. |
| Postcondition | Final formative/moderated score and full audit history exist. |

### UC-009 - Update Learner Model

| Field | Detail |
|---|---|
| Actor | LearnerModelService |
| Purpose | Produce valid knowledge and separate behavior scores. |
| Precondition | Evidence/behavior event changes. |
| Trigger | Grading completion or scheduled recompute. |
| Main Flow | 1. Keep only final valid non-appealed nonsuspect evidence. 2. Calculate version-specific difficulty/source/recency. 3. Calculate raw mastery, E, C, prior, effective mastery. 4. Apply `C>=0.35` plus five-response display gate. 5. Separately calculate engagement from at least two available components with renormalization/completeness. 6. Persist outputs. |
| Alternative Flow | Zero evidence uses prior internally and cold-start display. |
| Exception Flow | Invalid denominator/range produces logged calculation error, not corrupted score. |
| Postcondition | Planner receives mastery/confidence only; Intervention may receive engagement. |

### UC-010 - Generate Adaptive Study Plan

| Field | Detail |
|---|---|
| Actor | StudyPlannerService; Student; Teacher |
| Purpose | Create feasible, explainable daily/weekly learning. |
| Precondition | Active curriculum, coverage, calendar, enrollment, Student preferences. |
| Trigger | Nightly or any configured evidence, coverage, preference/blackout, exam/timetable, pin, missed-slot, or completion event. |
| Main Flow | 1. Filter using actual coverage. 2. Compute priorities. 3. Priority-aware topological order. 4. Compute cumulative feasibility at exact SubjectInstance exam dates across one combined 30-minute-block calendar. 5. Choose normal/triage. 6. Pack split Topic blocks and deterministic activities. 7. Include 30-minute 1/3/7/21 revisions. 8. Add factual reasons. 9. Publish idempotent version. |
| Alternative Flow | Runtime cycle uses unit-order fallback. |
| Exception Flow | Insufficient time emits CoverageDeficit to both actors and never silently omits Topics. |
| Postcondition | Current StudyPlan and optional deficit exist. |

### UC-011 - Learn with Plan and Tutor

| Field | Detail |
|---|---|
| Actor | Student; Tutor Agent |
| Purpose | Complete planned work and obtain grounded help. |
| Precondition | Student enrolled; plan/content available. |
| Trigger | Student opens a slot/material or asks Tutor. |
| Main Flow | 1. View reason/resource. 2. Consume approved material. 3. Ask question. 4. Retrieve approved chunks. 5. Return cited supported answer. 6. Record completion. |
| Alternative Flow | Unsupported question gets course-material refusal; LLM outage gets keyword results. |
| Exception Flow | An open assessment invokes concept-only lockdown until the entire session closes, even after early submission. |
| Postcondition | Learning/adherence event stored; no unauthorized content disclosed. |

### UC-012 - Practice and Replan

| Field | Detail |
|---|---|
| Actor | Student; System |
| Purpose | Build evidence and adapt future plans. |
| Precondition | READY approved Questions and Student enrollment. |
| Trigger | Student starts chosen/suggested practice, or an assigned Teacher publishes a configured quiz. |
| Main Flow | 1. For practice choose Topic/difficulty or accept weak-Topic suggestion; for quiz validate target Sections/Topics/blueprint/count/window/duration. 2. Select from the snapshotted READY bank. 3. Student submits. 4. Common grading runs. 5. Learner Model updates from eligible evidence. 6. Planner event is emitted. 7. Show feedback. |
| Alternative Flow | No eligible item returns controlled bank-review message. |
| Exception Flow | Duplicate event remains idempotent and does not add evidence twice. |
| Postcondition | New evidence and possible plan version exist. |

### UC-013 - Handle Intervention

| Field | Detail |
|---|---|
| Actor | Combined Agent; Teacher; Student |
| Purpose | Turn evidence into appropriate academic support. |
| Precondition | Configured detection rule is met. |
| Trigger | Nightly detection/event. |
| Main Flow | 1. Create evidence-backed Teacher alert. 2. Teacher reviews. 3. Teacher resolves/dismisses or approves/edits supportive message. 4. Student receives specific action if appropriate. 5. Record resolution. |
| Alternative Flow | Teacher resolves offline with reason and sends no platform message. |
| Exception Flow | Insufficient evidence or invalid scope suppresses alert; Student never sees internal label. |
| Postcondition | Alert is audited and resolved/open with Teacher ownership. |

### UC-014 - View and Export Reports

| Field | Detail |
|---|---|
| Actor | Teacher, Admin |
| Purpose | Review coverage, performance, mastery, or attendance within role scope. |
| Precondition | Authorized actor and report data. |
| Trigger | Select report and filters. |
| Main Flow | 1. Validate scope/date. 2. Query current data or daily snapshot. 3. Confidence-weight aggregates and show included/excluded counts/bands. 4. Suppress groups under five. 5. Display. 6. Export matching PDF/Excel. 7. Log export. |
| Alternative Flow | Narrow filters when dataset is empty/large. |
| Exception Flow | Cross-scope filters are rejected without partial data. |
| Postcondition | Consistent on-screen/exported report exists. |

### UC-015 - Record Manual Attendance

| Field | Detail |
|---|---|
| Actor | Teacher |
| Purpose | Supply the defined attendance source for Engagement and reports. |
| Precondition | Teacher is assigned to the SubjectInstance and its enrolled roster exists. |
| Trigger | Teacher opens or creates a dated/timed ClassSession. |
| Main Flow | 1. Validate ClassSession against the SubjectInstance. 2. Display enrolled roster. 3. Teacher marks PRESENT/ABSENT. 4. Validate scope/time/completeness. 5. Save atomically. 6. Audit actor/time. 7. Recalculate attendance component. |
| Alternative Flow | Teacher corrects a prior record; the new value and audit history are retained. |
| Exception Flow | Future date, unassigned SubjectInstance, non-enrolled Student, or incomplete/invalid state rejects the save without partial rows. |
| Postcondition | AttendanceRecord data is available to Section 24 and the Attendance Report. |

## 39. User Stories

### Admin Stories

**US-ADM-001 - Academic setup**  
As an Admin, I want to configure hierarchy, institution timezone, exact SubjectInstance exam dates, and recurring Section class/lab timetable, so that allocation, diagnostics, and planning use authoritative structure and time.  
**Acceptance:** GIVEN valid parent records/dates/times WHEN saved THEN they are scoped correctly; GIVEN missing parents, invalid dates, or overlapping timetable rows WHEN saved THEN the system rejects them clearly.

**US-ADM-002 - Automatic enrollment**  
As an Admin, I want Students auto-enrolled from Program + Semester + Section and assigned exactly one capacity-available Subject per required elective group, so that their list is complete without Student selection.  
**Acceptance:** GIVEN valid placement/offerings WHEN allocation runs THEN idempotent enrollments are created; GIVEN zero/multiple electives or exceeded capacity THEN confirmation is blocked; GIVEN Student mutation THEN `403`.

**US-ADM-003 - Staff allocation**  
As an Admin, I want one PRIMARY Subject Owner per shared Subject plus PRIMARY/CO assignments per SubjectInstance, so that operational scope and final approval authority are explicit.  
**Acceptance:** GIVEN valid assignments WHEN saved THEN assigned Teachers get instance operations and only the designated Subject Owner gets shared-artifact activation; GIVEN zero/multiple owners or an owner not PRIMARY on a related instance THEN activation is blocked.

**US-ADM-004 - Institution monitoring and entry diagnostics**  
As an Admin, I want to monitor Teacher allocation and coverage freshness and initiate semester-start prerequisite diagnostics, so that I can oversee academic progress and identify entry-level gaps.  
**Acceptance:** GIVEN authorized institution data WHEN I open the dashboard THEN I see allocations and stale coverage; GIVEN valid earlier-semester prerequisite Topics and a READY bank WHEN I create a session THEN it opens as configured; GIVEN a current-semester/non-prerequisite scope THEN it is rejected.

**US-ADM-005 - Promotion and transfer**  
As an Admin, I want to preview and confirm bulk semester promotion or Section transfer, so that placement changes are safe and historical evidence remains intact.  
**Acceptance:** GIVEN a valid operation WHEN previewed THEN additions/removals/capacity conflicts are shown without mutation; WHEN confirmed THEN current placement/enrollments change atomically and prior history remains resolvable.

### Teacher Stories

**US-TCH-001 - Versioned content**  
As an assigned Teacher, I want to upload DRAFT course material, and as PRIMARY Subject Owner I want to activate or roll it back, so that shared AI outputs stay traceable to approved sources.  
**Acceptance:** GIVEN an assigned Teacher uploads a file THEN a new DRAFT version is ingested without overwriting history; GIVEN a CO Teacher attempts activation THEN it is denied; GIVEN Owner rollback THEN old citations remain resolvable.

**US-TCH-002 - Curriculum approval**  
As an assigned Teacher, I want to edit/review the generated Topic graph, and as Subject Owner I want to activate or reject it, so that invalid AI structure never becomes live.  
**Acceptance:** GIVEN a validated draft WHEN the Owner approves THEN it becomes ACTIVE and prior active remains traceable; GIVEN a CO approval attempt or remaining cycle THEN activation is blocked.

**US-TCH-003 - Question approval**  
As a Teacher, I want to configure generation and review a reproducible 10% Topic/type/difficulty sample and Critic flags, so that only suitable Questions become READY.  
**Acceptance:** GIVEN a complete checked bank WHEN the Subject Owner approves THEN it becomes READY; GIVEN critical failure, missing artifacts, CO activation, or count above 200 THEN READY is blocked and correction/resampling is required.

**US-TCH-004 - Coverage update**  
As a Teacher, I want to update Topic coverage, so that diagnostics and study plans use actual syllabus progress.  
**Acceptance:** GIVEN an assigned Topic WHEN I select any valid forward/backward state THEN before/after/actor/time are stored and replan is queued; GIVEN a backward move THEN explicit confirmation is required; GIVEN a not-started prerequisite WHEN I mark covered THEN I see a warning but may confirm.

**US-TCH-005 - Checkpoint diagnostic**  
As a Teacher, I want to open a checkpoint for covered Topics, so that I measure retention of taught content.  
**Acceptance:** GIVEN only `COVERED`/`REVISED` Topics and sufficient five/six-item capacity WHEN I create the session THEN it is scheduled; GIVEN another state, over five Topics, or insufficient capacity THEN creation fails and names each issue.

**US-TCH-006 - Grade moderation**  
As a Teacher, I want a queue for low-confidence subjective grades and appeals, so that final academic feedback has human oversight.  
**Acceptance:** GIVEN confidence below `0.7` or an appeal WHEN I review THEN I can confirm/override with reason; GIVEN no reason for override THEN save is blocked.

**US-TCH-007 - Item quality**  
As a Teacher, I want suspect Questions flagged by response analysis, so that a bad item does not create false weakness.  
**Acceptance:** GIVEN `p < 0.15` or negative discrimination WHEN analysis runs THEN the item is flagged and excluded from mastery pending review.

**US-TCH-008 - Teacher-first support**  
As a Teacher, I want evidence-backed interventions routed to me first, so that Students receive suitable support rather than automated risk labels.  
**Acceptance:** GIVEN a configured detection threshold is met WHEN the nightly job runs THEN I receive evidence first; WHEN I message the Student THEN the text is specific/supportive and the action is audited.

**US-TCH-009 - Manual attendance**  
As a Teacher, I want to mark my enrolled roster present or absent for a dated/timed ClassSession, so that Engagement and Attendance Reports use a defined source.  
**Acceptance:** GIVEN my assigned SubjectInstance and valid ClassSession WHEN I save attendance THEN one audited record per enrolled Student is stored; GIVEN an unassigned instance, invalid time, or non-enrolled Student THEN the save is rejected.

**US-TCH-010 - Configured quiz**  
As a Teacher, I want to publish a one-attempt quiz to selected assigned Sections using Topics, blueprint/count, window, and duration, so that assessment scope is controlled.  
**Acceptance:** GIVEN sufficient READY capacity WHEN published THEN the exact bank version is snapshotted and target Students are notified; GIVEN insufficient capacity or an unassigned Section THEN publication is blocked.

### Student Stories

**US-STU-001 - Study preferences**  
As a Student, I want to enter availability, preferred time, blackouts, and learning preference, so that my plan fits my real schedule.  
**Acceptance:** GIVEN a valid recurring 30-minute grid in the institution timezone WHEN I save THEN the next plan uses it; GIVEN overlapping/invalid blocks or an attempt to edit official exam/timetable data THEN it is rejected.

**US-STU-002 - Controlled diagnostic**  
As a Student, I want to take an authorized diagnostic with autosave and a timer, so that my knowledge evidence is captured reliably.  
**Acceptance:** GIVEN an assigned open session WHEN I answer/refresh THEN saved answers return; GIVEN no open session WHEN I try to start THEN access is denied.

**US-STU-003 - Explainable plan**  
As a Student, I want daily/weekly Topics, revisions, and reasons, so that I understand what to study and why.  
**Acceptance:** GIVEN a generated plan WHEN I view a slot THEN Topic/time/activity/reason are shown; GIVEN insufficient total time THEN a TRIAGE label and full deficit appear.

**US-STU-004 - Grounded Tutor**  
As a Student, I want answers cited from approved course material, so that I can verify help against my syllabus.  
**Acceptance:** GIVEN supporting chunks WHEN I ask THEN the answer cites file/page; GIVEN no support THEN the Tutor refuses rather than using general knowledge.

**US-STU-005 - Fair assessment boundary**  
As a Student, I want active quiz answers protected, so that assessment evidence remains meaningful for everyone.  
**Acceptance:** GIVEN an open assessment WHEN an active item is pasted into Tutor THEN no answer is revealed and a neutral lockdown message appears; GIVEN early submission WHEN the session remains open THEN concept-only mode remains active.

**US-STU-006 - Practice feedback**  
As a Student, I want approved practice with misconception feedback, so that I can improve weak Topics.  
**Acceptance:** GIVEN eligible READY items WHEN I submit THEN common grading and learner update run; GIVEN a wrong mapped distractor THEN its rationale informs feedback.

**US-STU-007 - Honest mastery display**  
As a Student, I want a mastery number only when evidence is sufficient, so that I am not misled by early results.  
**Acceptance:** GIVEN `C < 0.35` or fewer than five final valid responses WHEN I view progress THEN I see `Building your profile`; GIVEN both gates pass THEN effective mastery may be shown.

**US-STU-008 - Grade appeal**  
As a Student, I want to appeal any formative grade, so that a Teacher can review possible error.  
**Acceptance:** GIVEN my formative grade WHEN I appeal with a reason THEN it is excluded from mastery and the Teacher is notified; GIVEN another Student's grade THEN I cannot view or appeal it.

**US-STU-009 - Approved recommendation**  
As a Student, I want resources matched to weak Topics, preference, and time, so that remediation is relevant and achievable.  
**Acceptance:** GIVEN approved matching resources WHEN recommendations run THEN each is ranked and Topic-mapped; GIVEN an unapproved resource THEN it is never shown.

### System Algorithm Stories

**US-SYS-001 - Valid mastery**  
As a project evaluator, I want mastery calculated by the published deterministic formula, so that results are reproducible and defensible.  
**Acceptance:** GIVEN fixed evidence WHEN the service runs repeatedly THEN outputs match; GIVEN hard Questions all wrong THEN difficulty does not raise mastery.

**US-SYS-002 - Feasible planning**  
As a project evaluator, I want feasibility checked before packing, so that the plan never hides uncovered work.  
**Acceptance:** GIVEN 40 required hours and 6 available hours WHEN planning runs THEN CoverageDeficit and TRIAGE list every unscheduled Topic.

## 40. Acceptance Criteria

The following compact scenarios cover important positive and negative paths. More boundary cases belong in the phase test suites.

| ID | Feature | Positive Scenario (Given / When / Then) | Negative Scenario (Given / When / Then) |
|---|---|---|---|
| AC-001 | RBAC/scope | GIVEN a Teacher assigned to Section A WHEN requesting its Students THEN only Section A records return. | GIVEN the same Teacher requests Section B WHEN unassigned THEN `403/404` returns with no data. |
| AC-002 | Auto-enrollment | GIVEN a CSE Semester 3 Section A Student and mapped offerings WHEN allocation runs THEN all applicable and Admin-assigned elective enrollments are created once. | GIVEN Student credentials WHEN enrollment mutation is requested THEN `403`; no row changes. |
| AC-003 | Calendar/timetable | GIVEN a valid term, institution timezone, exact SubjectInstance exam dates, and recurring Section class/lab timetable WHEN Admin saves THEN Planner reads normalized constraints. | GIVEN invalid date/time, missing exam deadline, or overlapping timetable rows WHEN saved THEN validation identifies each issue. |
| AC-004 | Ingestion | GIVEN a readable scanned syllabus WHEN ingested THEN OCR, <=800-token chunks with 120-token overlap, vectors, and source metadata are stored and traceable without crossing Unit boundaries. | GIVEN empty/unreadable extraction WHEN processed THEN asset fails clearly and no empty approved chunks appear. |
| AC-005 | Content version | GIVEN v1 active WHEN an assigned Teacher uploads v2 THEN v1 remains active/intact and v2 is DRAFT; WHEN PRIMARY Owner activates v2 THEN v1 is superseded but traceable. | GIVEN a CO/unassigned Teacher WHEN activation or rollback is attempted THEN access is rejected. |
| AC-006 | Graph validation | GIVEN A->B, B->A with confidence 0.8/0.4 WHEN validated THEN the 0.4 edge is dropped/flagged and result is acyclic; equal-confidence removal follows ascending edge IDs. | GIVEN an orphan or remaining cycle WHEN approval is attempted THEN activation is blocked. |
| AC-007 | Graph approval | GIVEN a valid DRAFT WHEN PRIMARY Subject Owner approves THEN it becomes ACTIVE and prior active is traceable. | GIVEN CO approval or a remaining cycle WHEN attempted THEN activation is blocked; if no active graph exists, only explicit Owner-approved flat fallback may activate. |
| AC-008 | Question schema | GIVEN a subjective/coding draft with rubric/3 tests/source WHEN saved THEN it is Critic-eligible. | GIVEN missing rubric, fewer than 3 code tests, or invalid source WHEN saved THEN validation fails. |
| AC-009 | Bank approval | GIVEN Critic-passed items and a passed reproducible 10% Topic/type/difficulty sample WHEN PRIMARY Owner approves THEN immutable bank becomes READY. | GIVEN any critical sample failure, CO approval, DRAFT/returned bank, or unresolved required correction WHEN serving/activation is attempted THEN it is blocked. |
| AC-010 | Diagnostics | GIVEN authorized actor, at most five Topics, 3-item blueprint, 10-60-minute/3-40-item limits, required five/six-item capacity, and READY bank WHEN session runs THEN seeded Medium-start selection is reproducible and stops at `C_session>=0.60`/limits before final grading. | GIVEN Student trigger, second attempt, late prerequisite window, >5 Topics, insufficient capacity, exposed item, or checkpoint Topic outside `COVERED`/`REVISED` WHEN requested THEN validation rejects and names the issues. |
| AC-011 | Coverage | GIVEN assigned Teacher and valid Topic WHEN state changes THEN status/actor/time persist. | GIVEN prerequisite is NOT_STARTED WHEN Topic is marked COVERED THEN warning appears but confirmed update is not blocked. |
| AC-012 | Stale coverage | GIVEN no update for seven days WHEN nightly job runs THEN persistent Teacher/Admin notifications occur and Planner uses the last actual state. | GIVEN stale data WHEN processing runs THEN no projected coverage is inferred or used; checkpoint still requires actual `COVERED`/`REVISED`. |
| AC-013 | Common grading/moderation | GIVEN all item types WHEN submitted THEN one flow writes uniform status-bearing ItemResponses; subjective confidence 0.70 finalizes while 0.69 remains pending/excluded. | GIVEN an appealed grade, override without reason, or unauthorized Teacher THEN evidence is excluded or mutation rejected as applicable, with audit. |
| AC-014 | Code sandbox | GIVEN Python 3.11 code that passes 2 of 4 equally weighted tests without timeout WHEN executed under fixed limits THEN score `0.5` and per-test results return. | GIVEN infinite loop, network access, >256 MB memory, >5 seconds/test, >30 seconds total, or >1 MB output WHEN executed THEN it is killed/blocked, timeout scores `0`, and the worker does not hang. |
| AC-015 | Mastery/item calibration | GIVEN fixed qualifying evidence WHEN computed THEN Section 23 matches; GIVEN 30 final valid same-Question-version responses across sharing instances THEN version difficulty/p-value/point-biserial are calculated. | GIVEN hard items all wrong, mixed Question versions, pending/appealed/suspect evidence, or fewer than 30 qualifying responses THEN mastery is not inflated and initial difficulty remains where applicable. |
| AC-016 | Confidence/cold start | GIVEN `C>=0.35` and five final valid Topic responses WHEN viewed THEN numeric effective mastery may appear. | GIVEN either gate fails or no evidence WHEN viewed/computed THEN no divide-by-zero or percentage appears; UI says `Building your profile` and prior stays internal. |
| AC-017 | Engagement separation | GIVEN two or three available components WHEN computed THEN weights renormalize and result is `Partial`; GIVEN all four THEN result is complete. | GIVEN fewer than two components or a partial score WHEN low-engagement detection runs THEN no low-engagement alert fires; Engagement never changes mastery/planning. |
| AC-018 | Eligibility | GIVEN a non-lab COVERED/REVISED Topic or IN_PROGRESS Topic with all prerequisite mastery `>=0.6` WHEN planning runs THEN it is eligible. | GIVEN a Core Lab, NOT_STARTED Topic, or IN_PROGRESS Topic with any prerequisite `<0.6` WHEN planning runs THEN it is excluded. |
| AC-019 | Priority | GIVEN known normalized inputs WHEN scoring runs THEN `P(t)` equals the exact weighted sum and explanation uses actual contributions. | GIVEN a high Engagement Score WHEN scoring runs THEN it adds exactly zero. |
| AC-020 | Combined feasibility/deficit | GIVEN multiple Subject deadlines sharing the same free time WHEN Planner runs THEN each 30-minute block is counted once and cumulative feasibility includes revisions; infeasibility produces one Student deficit with per-Subject/deadline breakdown and all unscheduled IDs. | GIVEN a Topic/revision cannot fit by its deadline WHEN output is written THEN it cannot disappear without deficit/pending state. |
| AC-021 | Packing/revision | GIVEN valid blocks/resources WHEN packed THEN prerequisite order, exact deadlines, 30-minute split slots, deterministic activity, no overlaps, and <=3 Topics/day hold; a first `0.7` crossing adds four 30-minute revisions. | GIVEN blackout/holiday/class/lab overlap, fourth Topic, or deadline violation WHEN evaluated THEN the slot is not placed there and any omission is reported. |
| AC-022 | Tutor/recommendation grounding | GIVEN an approved uploaded chunk above the active validated threshold WHEN queried THEN the answer has resolvable file/page citation; GIVEN approved resources/HTTPS links WHEN recommending THEN at most three Topic-mapped results return. | GIVEN insufficient chunks or an unapproved/out-of-Subject link WHEN processed THEN Tutor refuses/resource is filtered; external links are never crawled or cited as RAG evidence. |
| AC-023 | Lockdown/outage | GIVEN an assessment session still open and a query above the active validated Question-similarity threshold WHEN Tutor is called THEN concept-only lockdown returns no answer even after early submission. | GIVEN LLM outage WHEN Tutor is used THEN only keyword search over approved uploaded chunks appears, not fabricated prose. |
| AC-024 | Dashboard/report | GIVEN role-scoped current/daily-snapshot data WHEN viewed/exported THEN confidence-weighted aggregates, included/excluded counts/bands, and matching PDF/Excel appear. | GIVEN cross-scope filter or group size below five WHEN requested THEN unauthorized data/aggregate is suppressed while authorized row-level access remains unchanged. |
| AC-025 | Intervention | GIVEN any exact Section 28 threshold and no same-type alert in seven days WHEN detected THEN assigned Teacher sees evidence first and may send supportive wording. | GIVEN insufficient mastery/behavior evidence, active cooldown without severity increase, or proposed risk label WHEN processed THEN the alert/message is suppressed or requires correction. |
| AC-026 | Practice/quiz chain | GIVEN Student-selected/suggested practice or a valid Teacher-configured quiz WHEN submitted THEN Grading -> LearnerModel -> Planner event runs idempotently. | GIVEN duplicate event, second quiz attempt, superseded/suspect item, or 21-day reuse WHEN processed THEN no duplicate evidence/invalid serving occurs. |
| AC-027 | Student scheduling preferences | GIVEN a valid recurring 30-minute grid, preferred time, blackouts, and learning preference in the institution timezone WHEN saved THEN the next plan uses them. | GIVEN overlaps/invalid blocks or an attempt to edit official exam/timetable data WHEN submitted THEN validation rejects it. |
| AC-028 | Manual attendance | GIVEN an assigned Teacher, enrolled roster, and valid dated/timed ClassSession WHEN states are saved THEN one scoped audited record per Student is available to Engagement/reporting. | GIVEN another Teacher's instance, invalid/future session, or non-enrolled Student WHEN saved THEN the operation rejects without partial records. |
| AC-029 | Security/session | GIVEN a valid invitation/login WHEN used THEN setup and a four-hour JWT work over TLS; GIVEN reset/deactivation/Admin revocation THEN the prior token version is rejected immediately. | GIVEN expired/replayed setup/reset token, excessive attempts, secret in repository, or cross-scope ID WHEN tested THEN it is blocked/rate-limited and no protected data leaks. |
| AC-030 | Enrollment change | GIVEN a promotion/transfer WHEN previewed THEN changes/capacity conflicts appear without mutation; WHEN confirmed THEN placement changes atomically with history. | GIVEN an elective group with zero/multiple selections or exceeded capacity WHEN confirmed THEN operation is blocked. |
| AC-031 | Scale/accessibility | GIVEN 2,000 Student records, 100 authenticated concurrent users, and 60 simultaneous attempts WHEN load-tested THEN defined response/autosave targets hold; GIVEN major flows WHEN audited in current Chrome/Edge THEN WCAG 2.1 AA criteria pass. | GIVEN failed performance or accessibility gate WHEN release evidence is reviewed THEN the baseline is not accepted. |

## 41. Requirements Traceability Matrix

| Business Requirement | Functional Requirement(s) | Module | Actor | User Story | Acceptance Criteria |
|---|---|---|---|---|---|
| BR-001 | FR-ADM-001, FR-ADM-007 | M02, M04 | Admin | US-ADM-001 | AC-003 |
| BR-002 | FR-ADM-003..006, FR-STU-001 | M03 | Admin, Student | US-ADM-002, US-ADM-005 | AC-002, AC-030 |
| BR-003 | FR-CON-001..004 | M05 | Teacher | US-TCH-001 | AC-004, AC-005 |
| BR-004 | FR-CUR-001..004 | M06 | Teacher, Curriculum Agent | US-TCH-002 | AC-006, AC-007 |
| BR-005 | FR-QB-001..005 | M07 | Teacher, Assessment/Critic | US-TCH-003, US-TCH-007 | AC-008, AC-009 |
| BR-006 | FR-COV-001..004 | M08 | Teacher | US-TCH-004 | AC-011, AC-012 |
| BR-007 | FR-ADM-008, FR-DIA-001..006 | M09 | Admin, Teacher, Student | US-ADM-004, US-TCH-005, US-STU-002 | AC-010 |
| BR-008 | FR-GRD-001..007, FR-PRC-001..003 | M10, M15 | System, Teacher, Student | US-TCH-006, US-TCH-010, US-STU-006 | AC-013, AC-014, AC-026 |
| BR-009 | FR-LRN-001..004 | M11 | System, Student | US-STU-007, US-SYS-001 | AC-015, AC-016 |
| BR-010 | FR-TCH-003, FR-LRN-005 | M11, M17 | System, Teacher | US-SYS-001, US-TCH-008, US-TCH-009 | AC-017, AC-028 |
| BR-011 | FR-STU-002, FR-PLN-001..008, FR-DAY-001 | M12, M13 | System, Student, Teacher | US-STU-001, US-STU-003, US-SYS-002 | AC-018..021, AC-027 |
| BR-012 | FR-TUT-001..003 | M14 | Student, Tutor Agent | US-STU-004, US-STU-005 | AC-022, AC-023 |
| BR-013 | FR-GRD-004 | M10 | System, Teacher, Student | US-STU-006 | AC-014 |
| BR-014 | FR-GRD-005..006, FR-STU-006 | M10 | Teacher, Student | US-TCH-006, US-STU-008 | AC-013 |
| BR-015 | FR-REC-001 | M16 | Student, Combined Agent | US-STU-009 | AC-022 |
| BR-016 | FR-INT-001..002 | M17 | Teacher, Student | US-TCH-008 | AC-025 |
| BR-017 | FR-AUTH-001..004, FR-TCH-001, FR-NOT-001 | M01, M18 | All | US-ADM-003 | AC-001, AC-029 |
| BR-018 | FR-ADM-009, FR-RPT-001..003 | M18 | Admin, Teacher | US-ADM-004 | AC-024, AC-031 |

## 42. Priority

| Priority | Included Requirement Groups | Project Rationale |
|---|---|---|
| Must Have | Authentication/RBAC/security baseline; academic setup/allocation/promotion; auto-enrollment/elective capacity; exact exams/timetable; immutable ingestion/curriculum/bank ownership; question schema/Critic/sample approval/item analysis; Coverage Tracker/ClassSession attendance; diagnostics; practice/Teacher quizzes; common grading/moderation/appeal; exact Learner Model and Engagement separation; combined 30-minute Planner/deficit; daily plan/material; grounded Tutor/lockdown; persistent notifications; privacy/audit/failure behavior | These form the defensible end-to-end workflow and both original algorithms. |
| Should Have | Admin rollups; complete daily-snapshot dashboards and four report exports; unit bulk coverage; Teacher pins; Recommendation; Intervention | Project value, but richer analytical/recommendation surfaces may be reduced after core correctness is demonstrated. |
| Could Have | Diagnostic closing narrative; optional non-scoring coding-style comments; polished batch comparisons; additional chart drill-down | Useful presentation polish without changing the academic engine. |
| Future Scope | Section 47 items, including multi-college SaaS, ERP integration, native mobile, full proctoring, production HA | Not required for a final-year implementation. |

No Must-Have algorithm, approval gate, enrollment rule, diagnostic/grading separation, or deficit behavior may be removed to make room for a Should/Could feature.

## 43. Project Phase Mapping

Each phase should produce migrations, API endpoints/OpenAPI docs, Pydantic schemas, tests, seed/demo data, and relevant README documentation.

| Phase | Main Features | Requirements | Dependencies | Expected Demo |
|---|---|---|---|---|
| 1 - Foundation | Data model, Alembic, invitation/reset/revocable JWT/RBAC, hierarchy, Program-scoped Subjects, Subject Owners, exact exams/timetable, CSV import, capacity-aware electives, promotion/transfer, seed | FR-AUTH-001..004, FR-ADM-001..007, FR-STU-001 | None | Validate three roles, revocation, one Subject Owner per Subject, assigned Teacher per instance, read-only enrollment, one elective/group, and previewed transfer with history. |
| 2 - Ingestion & Curriculum | MinIO/OCR/chunks/embeddings, immutable shared versions, Subject Owner activation, Curriculum Agent, validation/editor/fallback | FR-CON-001..004, FR-CUR-001..004 | Phase 1 SubjectInstances/Teachers | Feed cyclic syllabus; CO edits but cannot activate; Owner activates corrected graph; prior active chain remains resolvable. |
| 3 - Assessment & Bank | Teacher blueprint, Assessment/Critic batch, item schemas, reproducible 10% sample/critical gate, READY version, exposure and item analysis | FR-QB-001..005 | Phase 2 active Topics/content | Generate configured count up to 200; block critical sample failure; demonstrate same-version 30-response calibration/point-biserial. |
| 4 - Coverage Tracker & Diagnostics | Four-state forward/backward UI, unit bulk update, actual-state-only alerts, session preflight, seeded adaptive selection/blueprint/exposure/stop, timed autosave | FR-COV-001..004, FR-DIA-001..006, FR-ADM-008, FR-STU-003 | Phase 3 READY bank | `REVISED` checkpoint succeeds; >5 Topics/short capacity fails clearly; early submission does not end Tutor lockdown. |
| 5 - Grading | Common AutoGrader, code sandbox, subjective Agent, misconceptions, moderation, appeals | FR-GRD-001..007, FR-STU-006 | Phase 4 attempts; Phase 3 grading artifacts | Infinite-loop code is killed/scored with timeout reason; low-confidence grade reaches queue; appeal/override audited. |
| 6 - Learner Model | ClassSession attendance, exact formulas, evidence statuses, same-version calibration, five-response display gate, partial Engagement, unit tests | FR-TCH-003, FR-LRN-001..005 | Phase 5 valid evidence; Phase 1 rosters | Test pending/appealed/suspect exclusion, hard-all-wrong, 30-response same-version calibration, two-component renormalization, and engagement independence. |
| 7 - Planner | Combined deadline-aware 30-minute algorithm, all key event triggers, feasibility/triage/Student deficit, deterministic activity packing, revisions/reasons | FR-PLN-001..008, FR-TCH-002, FR-STU-002..004 | Phase 6 mastery; Phase 1 exam/timetable/preferences; Phase 4 coverage | Shared availability counted once across Subjects; revision consumes capacity; infeasible deadline yields complete breakdown. |
| 8 - Daily Learning, Quiz & Tutor | Today's plan, material viewer, approved RAG, citations, refusal, session-close lockdown, outage fallback, unlimited practice and Teacher quiz | FR-DAY-001, FR-TUT-001..003, FR-PRC-001..003 | Phases 2, 3, 5, 6, 7 | Cited uploaded source; external link not crawled; pasted live item locked after early submit; quiz/practice update evidence idempotently. |
| 9 - Recommendation, Intervention, Notifications & Reports | Approved resource ranking, Teacher-first alerts, persistent in-app notices, daily snapshots, privacy-aware dashboards, PDF/Excel reports | FR-REC-001, FR-INT-001..002, FR-NOT-001, FR-RPT-001..003, FR-ADM-009 | All core phases | Group under five is suppressed; included/excluded counts display; dated snapshot reproduces; link recommendation is not crawled; four reports export. |

## 44. Assumptions

These are environmental conditions outside the product rules.

| ID | Assumption | Consequence if Incorrect |
|---|---|---|
| ASM-001 | The college provides accurate hierarchy, roster, calendar, Subject, Unit weightage, and Teacher-assignment data. | Allocation, urgency, reports, and access scope may be incorrect until the input data is corrected. |
| ASM-002 | Teachers provide legally usable course material and are available to approve curricula, banks, coverage, grades, and interventions. | AI-dependent academic workflows remain pending at their human gates. |
| ASM-003 | Students provide truthful availability/blackout preferences and participate in the planned demonstration. | Plan fit and user-evaluation findings may not reflect real behavior. |
| ASM-004 | The demonstration host supports Docker Compose, PostgreSQL/pgvector, Redis, MinIO, Celery, and the Python sandbox, with Internet access for configured LLM APIs. | AI calls or isolated code execution require an alternative demonstration environment; deterministic stored flows remain demonstrable. |
| ASM-005 | Real Student data is anonymized or replaced with synthetic data for project development and demonstrations. | College permission and a stricter data-handling process are required before real data is used. |

## 45. Constraints

- Final-year academic timeline requires phased delivery and prioritization of the two algorithms and hard business rules.
- The development team is limited in size and cannot responsibly build a commercial LMS/ERP at the same time.
- Demonstration infrastructure is limited; Docker Compose is the target, not a production cluster.
- LLM/API calls have cost, latency, quota, and outage constraints; batching, caching, budgets, and fallbacks are required.
- The project depends on usable college syllabus/content, academic calendar, roster, and allocation data.
- Teachers and Students must be available to validate workflows, language, item quality, and usability.
- Safe code execution is difficult; the demonstrated language remains Python 3.11 with the fixed limits.
- OCR and retrieval accuracy depend on source-file quality.
- Academic approvals and attendance processes may differ by college; this project implements only the requirements defined in this specification.
- The fixed source stack increases learning/integration effort but should not be expanded with unnecessary infrastructure.

## 46. Risks

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| LLM hallucination in curriculum/Tutor/grading | High | Medium | Approved-source grounding, citations, strict schema, confidence, Teacher gates, refusal/fallback. |
| Incorrect/ambiguous generated Questions | High | Medium | Critic, mandatory fields, Teacher sample/approval, duplicate checks, item analysis, suspect exclusion. |
| Insufficient real response data for calibration/evaluation | Medium | High | Keep initial difficulty below 30 responses; use seeded/synthetic non-claiming test data; report limitations. |
| LLM/API cost exceeds student budget | Medium | Medium | Batch jobs, per-subject budgets, caching, smaller model tier where appropriate, no live generation. |
| LLM/API outage | Medium | Medium | Retry/resume queue; existing bank; keyword Tutor fallback; deterministic services continue. |
| Student attempts to game unproctored quizzes | Medium | Medium | Lower source weights, randomization, time boxes, exposure controls, stronger supervised checkpoint evidence. |
| Incorrect interpretation of mastery as official ability | High | Medium | Confidence gate, explain formula/limits, knowledge-only inputs, formative framing, Teacher view. |
| Planner produces impossible or incomplete schedule | High | Low after tests | Calendar constraints, feasibility before packing, TRIAGE, explicit deficit, packing boundary tests. |
| Coverage not updated by Teachers | High | Medium | Single-click/bulk UI, persistent Teacher/Admin alerts, and explicit use of the last actual state only. |
| Code sandbox escape/resource exhaustion | High | Low/Medium | No network, non-privileged isolated container, strict limits, small supported language set, security tests. |
| OCR/poor source quality damages retrieval | Medium | Medium | Extraction validation, page traceability, Teacher preview/reupload, no empty approval. |
| Scope becomes too large for final year | High | High | Phase gates; protect Phases 1-8 core; reduce Recommendation/Intervention/dashboard polish first. |
| Privacy leakage across sections/departments | High | Medium | Query-layer RBAC, negative authorization tests, scoped exports/log access. |
| Incorrect implementation of thresholds/formulas | High | Medium | Treat Sections 21-25, 28, and 35-36 as versioned test fixtures; require boundary tests before phase acceptance. |

## 47. Future Scope

- Multi-college, multi-tenant SaaS with tenant isolation and subscription/operations tooling.
- Integration with ERP/SIS, attendance devices, calendars, and official examination systems.
- Student-ranked elective preferences; current allocation remains Admin-controlled and capacity-aware.
- Native Android/iOS app and offline content synchronization.
- Advanced predictive/cohort analytics beyond the defined deterministic mastery model.
- Full online proctoring, identity verification, plagiarism detection, and lockdown browser.
- Broader laboratory simulation and adaptive lab planning.
- Production high availability, autoscaling, disaster recovery, SIEM, SSO/MFA, WAF, and formal security program.
- Large-scale benchmarking across institutions and richer calibrated item-response models.
- Expanded coding languages and hardened multi-tenant execution infrastructure.

## 48. Final System Summary

UniAdapt AI supports exactly three roles: Admin, Teacher, and Student. Admin controls institution structure, Program/Semester Subjects, exact exam dates, Section timetable, one PRIMARY Subject Owner per shared Subject, SubjectInstance Teacher assignments, enrollment/electives, and placement changes. Students are automatically enrolled and never add/drop Subjects. Any assigned Teacher may prepare shared DRAFT content, curriculum, and banks; only the designated Subject Owner activates or rolls them back. Active versions remain operational and traceable until approved replacements activate.

Teachers maintain actual coverage with audited forward/backward changes. Admin-triggered prerequisite diagnostics run once per offering within the first 14 days; Teacher checkpoints accept actual `COVERED` or `REVISED` Topics. Both enforce five-Topic/40-item and bank-capacity limits. Teacher-created quizzes and unlimited eligible Student practice share the common grading flow. Objective/numerical/Python correctness is deterministic; rubric-based subjective grades apply high-confidence finalization, low-confidence moderation, and appeal of any formative grade.

Original Algorithm #1 computes knowledge-only Mastery from final valid nonsuspect evidence, with same-Question-version calibration and a confidence-plus-five-response display gate. Engagement remains separate and can be partial after renormalizing at least two available components. Original Algorithm #2 combines all Subjects, orders prerequisites deterministically, checks cumulative feasibility at exact exam dates, counts each 30-minute free block once, includes revision capacity, and produces one explained Student-level deficit when necessary.

Students use explainable plans, approved uploaded materials, cited RAG Tutor support, practice, quizzes, feedback, and recommendations. Tutor concept-only mode lasts until the full assessment session closes; external HTTPS resources may be recommended but are never crawled or used as RAG evidence. Persistent in-app notifications, daily report snapshots, confidence-weighted privacy-aware aggregates, and four practical exports close the loop. AI uses a deployment-selected OpenAI or Anthropic adapter with minimized pseudonymous data; deterministic services and human approval retain academic control.
