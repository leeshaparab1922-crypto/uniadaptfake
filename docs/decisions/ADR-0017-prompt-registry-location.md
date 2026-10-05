# ADR-0017: Versioned prompt registry location and format

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Phase 2 (Curriculum Agent, the first prompt); every later agent phase (3, 5, 8, 9)
- **SRS refs:** NFR-MNT-001 ("prompts shall be outside business logic in a versioned registry"); NFR-DAT-002; NFR-AI-002; Section 18 "AI control"; Section 32; Section 31.3 AIProviderConfiguration / AgentRun; NFR-SEC-011; `.claude/rules/deterministic-services.md`

## Context
- NFR-MNT-001 requires prompts to live outside business logic, in a
  **versioned registry**.
- NFR-DAT-002 requires prompt versions to stay resolvable after a later
  version is activated. NFR-AI-002 requires every LLM call to record its
  versioned prompt.
- The SRS does not say where the registry is stored, what format it uses, or
  how a version is identified. Phase 2 creates the first prompt, so this
  decision sets the pattern for every later agent.

## Options

### A. Files in the repository only
`backend/app/prompts/<agent>/<version>.toml`, loaded at runtime. Each
`agent_runs` row records the agent name and version string.
- **Pros:** Prompts are reviewed in PRs like code, with diffs and history.
  Simple.
- **Cons:** Being "resolvable" depends on git history. If a version file is
  edited in place or deleted, old `agent_runs` rows point at text that no
  longer matches, and nothing in the database detects it. There is no
  foreign key from `agent_runs`.

### B. Database table only (`prompt_versions`), edited through an Admin UI
- **Pros:** Immutable rows, a foreign key from `agent_runs`, and runtime
  changes without a deploy.
- **Cons:** Prompts are changed outside code review, so a prompt change
  could reach an agent's output schema without being reviewed with the
  matching Pydantic schema. The SRS defines no Admin UI or role permission
  for editing prompts, so building one goes beyond what the SRS defines.

### C. Repo files as source of truth, synced into an immutable DB table (recommended)
- Prompts are written as `backend/app/prompts/<agent>/v<N>.toml`. Each holds
  the system and user templates, the name of the Pydantic output schema, and
  notes.
- At application or worker startup, a loader computes a SHA-256 hash of each
  file's content and **inserts** it into an append-only `prompt_versions`
  table (`agent`, `version`, `content_sha256`, `body`, `output_schema`,
  `created_at`). If a row for `(agent, version)` already exists with a
  **different** hash, startup fails, so an edit in place is caught.
- `agent_runs.prompt_version_id` is a foreign key to that row.
- **Pros:** Combines code review from A with immutable, foreign-key
  resolvability from B. Detects edits in place. No new UI or role
  permission.
- **Cons:** Needs a small startup sync step and one extra table.

## Recommendation
**Option C.** Prompt files are TOML, read with Python 3.11's built-in
`tomllib`, so no new dependency is needed. Templates use the standard
library's `string.Template`, or LangChain's `PromptTemplate` since LangChain
is already in the fixed stack. The Phase 2 plan picks one and every agent
uses it.

Why:
1. It is the only option where NFR-DAT-002's "remain resolvable" is enforced
   by the database. Options A and B rely on discipline or lose review.
2. Prompt changes are reviewed in the same PR as the Pydantic output schema
   they must match (Section 18 "strict Pydantic output").
3. Prompts stay entirely outside service code, as NFR-MNT-001 and the
   deterministic-services rule require. The five deterministic services
   never import from `app/prompts/`.

## Consequences if accepted
- New directory `backend/app/prompts/`, a `prompt_versions` table (Phase 2
  migration), and a foreign key from `agent_runs`.
- The rule is "new file, new version": a change is always a new `v<N+1>`
  file, never an edit to an existing version file. The startup hash check
  enforces it.
- Prompt files must not contain secrets or Student data (NFR-SEC-011).
  Templates only describe where pseudonymous input goes.
- If runtime prompt editing is ever needed, it requires a new ADR and an SRS
  role-permission decision.
