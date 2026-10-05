# ADR-0016: LLM provider adapter and model for the Curriculum Agent

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Phase 2 (Curriculum Agent; the first provider adapter built); later agent phases reuse the adapter but choose their own models
- **SRS refs:** FR-CUR-001; Section 18 "AI control" row; Section 32 (provider-neutral interface, OpenAI or Anthropic adapter); Section 31.3 AIProviderConfiguration / AgentRun; NFR-AI-002; NFR-SEC-011; ASM-004; `.claude/rules/deterministic-services.md`

## What the SRS already settles (not re-decided here)
Section 32 says: *"All agents use a provider-neutral interface; deployment
configuration selects either the OpenAI or Anthropic adapter and named
model."* So:
- Only two providers are allowed: **OpenAI or Anthropic**. No other provider
  is an option.
- The interface must be provider-neutral, and the model is selected by
  deployment configuration, not hard-coded.
- Every call must have a versioned provider, model, prompt, and
  configuration, a strict Pydantic output, retry-with-repair, a token budget,
  and an `agent_runs` log.

## What is still open
1. Which adapter Phase 2 builds first. Section 43 puts Phase 2 first, and it
   is the first phase with an LLM call.
2. The default model configured for the Curriculum Agent in the
   demonstration deployment.

The Curriculum Agent is a low-volume batch task: one run per requested
Subject or version. It does structured extraction from a syllabus to Units,
Topics, outcomes, Bloom level, hours, and prerequisite edges with
confidence. Mistakes are caught by deterministic validation (FR-CUR-002) and
by Teacher review and Owner approval (FR-CUR-003/004), so quality matters
more than latency or per-call cost.

## Options

### A. Anthropic adapter, `claude-opus-5-5` (recommended)
- The current Opus model. It has a 1M-token context, so a whole syllabus fits
  in one call with no chunked map-reduce. It costs $4 / $20 per million
  input/output tokens.
- **Pros:** The most capable model of the three for long, multi-constraint
  structured extraction, such as prerequisite edges with calibrated
  confidence and earlier-semester scope checks. At these volumes the cost is
  small: a 50k-token syllabus with about 16k tokens of output is under $1
  per run.
- **Cons:** The highest per-token cost of the three options. Some API
  behaviour differs from older models (see Consequences).

### B. Anthropic adapter, `claude-sonnet-5-5`
- The current Sonnet model, with a 1M-token context, at $2 / $10 per million
  input/output tokens.
- **Pros:** Half the cost of Opus 5.5 and faster. Probably good enough for a
  syllabus that is already well structured.
- **Cons:** Cutting cost is a human choice, not an agent default, and there
  is no measured quality data for this task yet. If chosen, it should be
  checked on the same sample syllabi as Option A.

### C. OpenAI adapter, a named OpenAI model
- Allowed by Section 32. The specific model name should be chosen by a
  human; this ADR does not name one it cannot verify.
- **Pros:** Useful if the college or demonstration host already has OpenAI
  credits or credentials.
- **Cons:** Phase 2 would build the OpenAI adapter first instead. Either way,
  the second adapter has to be built eventually to satisfy Section 32's
  "either" requirement.

## Recommendation
**Option A. Phase 2 builds the Anthropic adapter first (through LangChain's
Anthropic integration, `langchain-anthropic`, since LangChain is in the fixed
stack) and sets the Curriculum Agent's default model to `claude-opus-5-5`.**
The provider and model stay deployment configuration, as Section 32
requires, so switching to Option B or C is a configuration change plus a new
`AIProviderConfiguration` version, not a code change.

Why:
1. This is the batch extraction step every later phase depends on. Errors in
   the topic graph flow into question generation, the Learner Model, and the
   Planner. The most capable current model is worth it at one run per
   Subject.
2. A 1M-token context means one call per syllabus, which keeps
   `agent_runs` traces and source references simple.
3. The cost is predictable and small. Batch processing could reduce it
   further if needed.

## Consequences if accepted
- `langchain-anthropic` is added as the LangChain provider integration for
  the Anthropic adapter. The OpenAI adapter (`langchain-openai`) is still
  required by Section 32 and is scheduled by the Phase 2 plan, either in
  Phase 2 or as a named follow-up. This ADR does not decide that timing.
- **API behaviour the Phase 2 plan must handle for `claude-opus-5-5`:**
  - Forced tool choice (`tool_choice` `any` or a named tool) is rejected with
    HTTP 400. Strict Pydantic output must use native structured outputs (a
    JSON-schema output format) or `auto` tool choice with `strict: true`. The
    plan must confirm which mode `langchain-anthropic`'s structured-output
    helper uses for this model.
  - Thinking cannot be disabled, and effort defaults to `medium`. The effort
    level is set explicitly and recorded in the provider configuration
    version.
  - `temperature`, `top_p`, and `top_k` cannot be set. Reproducibility comes
    from versioned prompt and model configuration plus the full
    `agent_runs` input/output log, not from fixed sampling settings.
    Determinism stays in the deterministic validators (FR-CUR-002), as the
    deterministic-services rule requires.
  - Handle the `refusal` stop reason as a failed run with retry-with-repair
    or a safe failure, never as an empty graph.
- The API key comes only from environment or secret management
  (NFR-SEC-013). Syllabus chunks contain no Student data. Any future
  Student-related input must still follow NFR-SEC-011 minimisation.
- ASM-004 applies: without Internet access to the provider, curriculum
  generation fails safely and the Owner can still activate a flat
  Unit-order version (FR-CUR-004).
