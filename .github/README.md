# UniAdapt AI — GitHub Copilot workflow

This is the Copilot port of the complete `.claude` workflow inspected on
2026-09-16. The installed CLI reports **1.0.85**. Only new files under `.github`
were created; `.github` did not exist beforehand. `.claude` remains unchanged.
The source workflow and full coding rules are retained, with explicit runtime
adapters rather than Claude configuration pasted into Copilot configuration.

## Read these limitations first

- Copilot's documented `preToolUse` input has no reliable custom-agent identity.
  An Agent 1-specific hard block cannot be reproduced for arbitrary `/agent`
  switching or concurrent subagents. Do not infer identity from `sessionId`,
  user text, invented `agent_type` fields, or the most recent subagent event.
- The native publication hook requests human inspection for publishing and opaque
  shell commands in **all** sessions. Ordinary commands and literal mentions such
  as `echo "git push"` are unaffected. The main session is not mislabeled Agent 1.
  Reject publication for Agent 1; Agent 2 still needs PASS and fresh ship approval.
- The dedicated Agent 1 launcher additionally denies recognized publication
  commands using a process-environment session restriction and CLI denial rules.
  This is a launch contract, **not Copilot-provided identity**. It lasts for that
  entire session, including any agent switch. Exit before launching Agent 2.
  A user-editable hook/environment is not a tamper-proof sandbox.
- Native file writes to SRS paths are denied; malformed write arguments fail
  closed. Explicit shell SRS writes are denied, and opaque commands require review.
  A hook cannot prove the behavior of arbitrary scripts, aliases, interpreters,
  MCP servers, network clients, or commands which compute paths at runtime.
  Their no-SRS-write/no-Agent-1-publication policies remain binding instructions.
- GitHub documents command-hook **timeouts as fail-open**, including pre-tool
  hooks. Disabled hooks, missing repository trust, configuration rejection, or
  timeouts prevent an absolute enforcement guarantee. Do not call this fully
  equivalent enforcement; inspect `/env` and hook warnings before real work.
- No live model-driven Copilot session, application deployment, or shipping was
  executed as validation. Tests exercise the adapters directly. The source live
  verification procedure remains unverified until an application exists.

## Layout and complete source mapping

GitHub documents repository instructions in `copilot-instructions.md`, modular
instructions in `instructions/*.instructions.md`, agents in `agents/*.agent.md`,
skills with `SKILL.md` and adjacent resources in `skills/`, and hook JSON in
`hooks/*.json`, all under `.github`. Supporting wrappers, documentation and tests
stay here too; there is no invented root config, workflow action, or dependency.

| Source component | Copilot implementation under `.github/` | Treatment |
| --- | --- | --- |
| `.claude/agents/phase-planner-implementer.md` | `agents/phase-planner-implementer.agent.md` | Full planning/implementation steps; supported tools; explicit skill loading; no publishing |
| `.claude/agents/implementation-verifier-shipper.md` | `agents/implementation-verifier-shipper.agent.md` | Full verification/shipping steps; independent review; no code patching; fresh approval |
| `.claude/rules/general.md` | `instructions/general.instructions.md` | Complete fixed stack, testing, security and architecture rules; included repository-wide |
| `.claude/rules/backend.md` | `instructions/backend.instructions.md` | Complete content; `applyTo: backend/**` |
| `.claude/rules/frontend.md` | `instructions/frontend.instructions.md` | Complete content; `applyTo: frontend/**` |
| `.claude/rules/deterministic-services.md` | `instructions/deterministic-services.instructions.md` | Complete content; services and SRS path scopes |
| `.claude/skills/phase-status/SKILL.md` | `skills/phase-status/SKILL.md` | Name, description, operational instructions preserved |
| `.claude/skills/phase-status/check.py` | `skills/phase-status/check.py` | Same heuristic/status output; exclude all workflow scaffolding |
| `.claude/skills/srs-lookup/SKILL.md` | `skills/srs-lookup/SKILL.md` | All query forms and usage caveats preserved |
| `.claude/skills/srs-lookup/lookup.sh` | `skills/srs-lookup/lookup.sh` | Original executable logic, same relative depth; explicit Bash invocation |
| `.claude/skills/update-claude-md/SKILL.md` | `skills/update-claude-md/SKILL.md` | Still updates **CLAUDE.md**, only when authorized |
| `.claude/skills/update-claude-md/generate.py` | `skills/update-claude-md/generate.py` | Same marker/status generator; workflow link and runtime wording adapted |
| `.claude/skills/verify-live/SKILL.md` | `skills/verify-live/SKILL.md` | Full static/live steps, examples, safety notes, evidence limitations |
| `.claude/skills/verify-live/scripts/audit_phases.py` | `skills/verify-live/scripts/audit_phases.py` | Same status/range/trace/report logic; exclude workflow/docs evidence |
| `.claude/hooks/block-srs-doc-edits.sh` | `hooks/scripts/block-srs-doc-edits.sh`, `.ps1`, shared `policy.py` | Native payload, normalized targets, fail-closed writes |
| `.claude/hooks/block-agent1-publish.sh` | `hooks/scripts/block-agent1-publish.sh`, `.ps1`, shared `policy.py` | Shared approval backstop; dedicated launch restriction; identity gap disclosed |
| `.claude/hooks/format-on-write.sh` | `hooks/scripts/format-on-write.sh`, `.ps1`, shared `policy.py` | Best-effort, one-target formatter commands, bounded runtimes |
| `.claude/settings.json` | `hooks/uniadapt.json` | Version 1; native lower-camel events, platform command fields, timeouts |
| `.claude/README.md` | This README and `validation/RESULTS.md` | Full operational mapping, use, validation and limitations |
| Root `CLAUDE.md` context; phase state and templates | `copilot-instructions.md` plus references to unchanged originals | Project context, SRS authority, process and traceability retained |

No source skill resource was omitted. The Windows lookup adds `lookup.py` and
`lookup.ps1`; all other source skill resources remain in the same relative
locations. The complete list of created files is below.

## Agents, approval and shipping

In an interactive Copilot CLI session use `/agent` to select either role, or
`/agent phase-planner-implementer` and `/agent implementation-verifier-shipper`.
The installed command help confirms `/agent [name]` and the `--agent` option.

```powershell
# Recommended dedicated Agent 1 session; resolves repo from the launcher path:
pwsh -NoProfile -File .github/copilot/agent1.ps1 -Prompt 'Plan phase 1, then stop.'

# Direct documented custom-agent mechanism (shared hook, no launcher restriction):
copilot --agent=phase-planner-implementer
copilot --agent=implementation-verifier-shipper
```

On Linux/macOS use `bash .github/copilot/agent1.sh 'Plan phase 1, then stop.'`.
Examples above assume a repository-root shell; otherwise pass the absolute script
path. The launcher sets `-C` to the derived repository root. Launch Agent 2 from
the repository or use `copilot -C <repo> --agent=implementation-verifier-shipper`.
The documented programmatic form is `copilot --agent=<name> --prompt "..."`;
prefer interactive use for these human gates. CLI 1.0.85 says noninteractive
prompt mode requires tool approval configuration; **do not use allow-all or
autopilot to substitute for workflow approval**.

The sequence remains plan → human review/approval → implement → human request to
verify → verify/review → fresh human shipping approval → branch/commit/push/PR.
Every transition ends the agent turn. The main session records `plan_approved`
only after actual approval. A pending `planned` phase is not replanned; an approved
phase resumes implementation. Review failures produce BLOCKED, never hidden fixes.
Ship approval resumes Step 7 of the already verified phase; it is not a request to
find a new `implemented` phase. Reverify if the reviewed changes changed.

`docs/phase-state.json` remains the phase-progress source of truth, cross-checked
against actual deliverables. Keep existing keys, phase numbering, Section-43
dependencies, timestamps and paths. Use the existing `docs/templates` plan/report
structures and record exact FR/BUS/AC evidence. Static ID presence is not proof of
correctness. Section 23/24/25 math must be checked line by line, including constants,
ordering and boundary cases; Engagement Score must never change Mastery Score.

Claude frontmatter was reviewed field by field: names/descriptions are retained;
Read/Grep/Glob/Write/Edit/Bash become supported read/search/edit/execute aliases;
Agent becomes the agent alias only for the verifier. Claude `sonnet`, permission
mode, turn limits, color and skill-preload fields are omitted. The model inherits
the Copilot session model. There is no claimed equivalent of a 40/60-turn cap or
Claude permission mode. Read/write scope and skill preloading are explicit agent
instructions; edit-tool access alone does not enforce the verifier's file list.

The source `agent-skills:code-reviewer` is an external Claude plugin, not present
in `.claude`. Copilot's documented built-in `code-review` agent is the adapter.
Pass it correctness, readability, architecture, security and performance, all
four rules and the phase's requirement IDs. If independent review is unavailable,
record BLOCKED. Do not silently substitute self-review. No reviewer plugin was
installed and no new third workflow role was invented.

The source requires `Co-Authored-By`, `Claude-Session`, and a Generated-with-Claude-Code
footer, but defines no identity or session values. Preserve genuine attribution;
Copilot work must use truthful Copilot attribution and a real session identifier
if one is available. Do not invent a Claude session or author identity. Resolve
missing mandated attribution with the human before committing. This is an explicit
attribution adapter, not a claim of byte-for-byte footer equivalence.

## Skills and helper behavior

Use `/skills reload`, then `/skills info phase-status` (and the other names) to
check selection. Invoke by name in a prompt, for example `Use /srs-lookup for
FR-AUTH-001`. CLI discovery on this machine selects the four `.github` versions
over the same names in `.claude`/`.agents`. `update-agents-md` remains separately
discoverable from `.agents`; it is not part of this Copilot workflow. Do not call
it as a substitute for update-claude-md. No global settings were changed.

From the repository root:

```text
python -B .github/skills/phase-status/check.py
bash .github/skills/srs-lookup/lookup.sh FR-AUTH-001
bash .github/skills/srs-lookup/lookup.sh 23
pwsh -NoProfile -File .github/skills/srs-lookup/lookup.ps1 "phase 1"
python -B .github/skills/verify-live/scripts/audit_phases.py
python -B .github/skills/verify-live/scripts/audit_phases.py 1
```

The adjacent Python lookup works without Bash: `python -B
.github/skills/srs-lookup/lookup.py "phase 1"`. All helpers derive the repository
from their script location. When invoked from any other directory, use an absolute
quoted script path, or change to the skill's base directory identified by SKILL.md.
No injected Claude path variables or unresolved argument placeholders are used.

`check.py` retains the conservative deliverable-name heuristic, MISMATCH reporting
and exit 0 for a completed check (including a mismatch), exit 1 for missing state.
`lookup.sh` retains one-query arguments and success 0/missing-invalid 1. The Python
adapter matches successful output including line numbers. The source comment's
`Section 43` example is not implemented by its parser: use `43`.

`audit_phases.py` retains the no-argument claimed-status audit and optional forced
phase number, ID-range expansion and report checks, exit 1 for detected gaps and
0 otherwise. The script actually uses state-file requirement ranges; it does not
derive every BUS/AC relationship from the SRS. Missing plans are reported; missing
PASS sets a gap specifically for verified/shipped phases. Agent instructions still
require fresh SRS/plan cross-checks, negative tests and live verification. The
ported scanners exclude `.github`, `.agents`, `.claude`, docs and SRS scaffolding
so this port cannot masquerade as application evidence. This fixes a source
exclusion mismatch while retaining the heuristic's intended scope.

`generate.py` still reads phase state and creates/replaces/appends the marked
status section in root **CLAUDE.md**. Its actual markers include
`(update-claude-md skill)`. It preserves the source generator's surrounding-text
behavior, including newline normalization. Run it only when root-file writes are
authorized in future implementation work. It was **not run against root CLAUDE.md**
during this port; generator tests redirect its paths to isolated `.github` fixtures.

The full verify-live skill retains Compose startup, readiness polling, browser/API
flows, evidence recording and clean shutdown. Ports, credentials and chromium-cli
examples are source placeholders, not confirmed deployment facts. Windows users
need Git Bash for those shell examples or equivalent PowerShell commands after
checking the actual application's configuration. No app, browser dependency, or
container was installed/started during validation.

## Instructions and legacy coexistence

`copilot-instructions.md` provides project context and human gates, and uses the
documented relative `@instructions/general.instructions.md` include so general
rules apply even without a file match. The same rule also has `applyTo: "**"`.
The other `applyTo` values are `backend/**`, `frontend/**`, and
`backend/app/services/**,SRS_Doc/**`. Commas separate patterns. All four full rule
bodies remain; no fixed-stack, purity, coverage, JWT, upload, sandbox-resource,
logging, authorization, schema, migration, naming or formatting requirements
were replaced by a summary. Formula text stays authoritative in the unchanged
SRS and is retrieved via the lookup skill rather than duplicated and allowed to drift.

Inspect `/instructions`; restart/resume or start a new session after instruction
changes. Restart CLI after hook edits. Agents use the documented `.agent.md`
suffix and are available to the main session through `/agent`/`--agent`.

Current GitHub docs also say Copilot loads `AGENTS.md`, `CLAUDE.md`, `.claude/agents`,
`.claude/skills`, and inline hooks from `.claude/settings.json`. Agent priority
favors `.github` at the same level; skills priority was confirmed locally. The
instruction sources combine without a general precedence guarantee. Existing
root files refer to Antigravity/Claude; the new instructions explicitly direct
Copilot to these native paths. **No existing file was changed to resolve this.**

Legacy inline hooks may coexist with native hooks. The legacy Bash hooks use
Claude-only command variables/payloads, and their successful execution under
Copilot is not assumed or certified. This port never invokes them or depends on
their output. Inspect `/env` and warnings in a future interactive session; if a
legacy hook conflicts, stop and report its exact origin. Do not edit `.claude`,
disable all hooks, or claim the native adapter can cancel an independently loaded
hook. Combined live-session behavior is a remaining validation gap under the
preservation constraint. The stale comment in the original publication script
mentions a settings deny rule, but the actual source settings contain hooks only;
this port does not claim that missing deny rule exists.

## Hook contract and platforms

`hooks/uniadapt.json` uses version 1 and `preToolUse`/`postToolUse`. Each entry has
`type: command`, explicit `bash` and `powershell` commands, repository-relative
`cwd: "."`, and a timeout in seconds (10 for safety checks, 25 for formatting).
There are no Claude matchers or nested hook arrays. Wrappers locate `policy.py`
from their own directory, not the caller's working directory. Explicit
`bash script.sh` and `pwsh -NoProfile -File script.ps1` require no executable bit
or Git mode change. Bash uses python3, falling back to python. PowerShell uses
python, falling back to python3. Windows requires PowerShell 7+ and Python 3.11+;
the Bash lookup also needs grep/awk/sed/cut/head/wc (Git Bash provides them).
No jq, npm download, pip install, or execution-policy change is used.

The camelCase envelope is `{sessionId, timestamp, cwd, toolName, toolArgs}`;
post-tool also contains `toolResult`. `toolArgs` is documented as unknown, so the
adapter accepts an object or a JSON-encoded object. Native create/edit paths use
`path`; `filePath` and `file_path` are explicit compatibility adapters within
`toolArgs`, not Claude's envelope. Patch adapters enumerate all Add/Update/Delete/
Move-to headers; multi-edit adapters enumerate every replacement. Move/rename
checks both source and destination and fails closed on an unknown shape. The
read-only str_replace_editor view subcommand remains allowed. Unknown external
mutation tools must supply an identifiable safe target and still require review.
Tool-specific schemas beyond these fixtures have not been observed in a live
Copilot model call; unfamiliar writes must fail closed rather than guess.

Paths are checked case-insensitively with both slash styles, relative cwd,
drive/UNC paths, nested SRS directories, traversal, Windows trailing dots/spaces,
and host-resolvable symlinks/junctions. Every identified target is checked; text
inside an unrelated document mentioning SRS_Doc does not count as a target.

Pre-hooks emit one JSON object with `permissionDecision: "deny"` and a reason for
blocked operations, or `"ask"` for inspection, or `{}` to retain normal permissions.
They never emit `allow`, which would preapprove a tool. Malformed envelopes and
file/shell arguments return deny; known read-only tools need no write-path parsing.
Unexpected pre-hook errors and a missing interpreter return a denial. All wrappers
return exit 0 with the decision encoded in stdout. Copilot's documented command
crash and timeout handling remains outside the script's control.

The publication parser recognizes executable command segments after shell
operators, global Git/GH options, quoted executable paths, env/command wrappers,
and nested common shells. It catches git push/send-pack/http-push, all gh pr,
gh API/release, common package/container publishing and deployment/copy commands.
It does not confuse echo/printf/Write-Output literal documentation with execution.
Computed commands, substitutions, aliases and arbitrary scripts get human review;
the parser is deliberately not advertised as a complete shell interpreter.
For cloud-agent jobs GitHub treats `ask` as deny, so unattended shipping is not
equivalent to this interactive human-gated CLI workflow.

Formatting runs only after a successful recognized file write. It resolves the
real target, refuses SRS/outside-repo files, and passes one file per formatter
command. Backend `.py` uses installed Ruff check --fix and format with --no-cache
and a Ruff config present. Frontend `.ts`/`.tsx` uses Node plus repository-local
ESLint/Prettier entry points and configs, without npx downloads. Commands run in
the backend/frontend directory with a 4-second individual and 16-second aggregate
budget. Missing files, directories, configs or tools safely no-op. Formatter
errors/timeouts are swallowed, all output suppressed, and the post-hook always
returns `{}`/0 so the original write stays valid. Arbitrary formatter plugins are
trusted project tooling, not sandboxed by this hook. Mocked target-scope tests
and real no-op fixtures confirm the adapter does not target unrelated files.

## Equivalence classification

| Behavior | Classification and evidence |
| --- | --- |
| Complete project/rule/phase/SRS/acceptance policies | Preserved operational content; instruction-enforced as in source |
| Bash lookup queries and exit behavior | Equivalent logic; successful output and negative exits checked against native adapter |
| Phase-status and audit helpers | Adapted only for root references/scaffold exclusions; original heuristic limits retained |
| CLAUDE.md status generation | Equivalent create/replace/append behavior in isolated fixtures; workflow attribution/link adapted |
| Native file SRS protection | Adapted and strengthened; tested payload/path/patch cases, not a universal filesystem sandbox |
| Format-after-write | Adapted; safe no-op and exact target/tool selection tested; real app formatting not run |
| Approval gates/verifier write scope | Instruction-enforced; hooks cannot authenticate a conversation approval or active verifier |
| Agent 1-only publication denial | Not enforceable from native tool-hook identity; shared ask plus dedicated session denial adapter |
| Independent reviewer | Copilot built-in reviewer adapter; unavailable reviewer blocks verification |
| Model/turn/color/permission-mode fields | Claude-specific controls not ported; session model and normal Copilot permissions apply |
| Absolute protection against timeout/bypass/arbitrary shell writes | Not enforceable by these repository hooks; explicitly not claimed |

## Validation and complete created-file inventory

See [validation/RESULTS.md](validation/RESULTS.md) for commands and recorded results.
Tests create temporary fixtures only under `.github/validation` and remove only
those owned fixtures. `-B` prevents Python cache creation. No application files
are formatted or modified. A SHA-256 baseline includes all 220 original files,
including `.git`; `check_preservation.py` never restores or changes anything.

```text
.github/
  README.md
  copilot-instructions.md
  agents/
    phase-planner-implementer.agent.md
    implementation-verifier-shipper.agent.md
  copilot/
    agent1.sh
    agent1.ps1
  hooks/
    uniadapt.json
    scripts/
      policy.py
      block-srs-doc-edits.sh
      block-srs-doc-edits.ps1
      block-agent1-publish.sh
      block-agent1-publish.ps1
      format-on-write.sh
      format-on-write.ps1
  instructions/
    general.instructions.md
    backend.instructions.md
    frontend.instructions.md
    deterministic-services.instructions.md
  skills/
    phase-status/SKILL.md
    phase-status/check.py
    srs-lookup/SKILL.md
    srs-lookup/lookup.sh
    srs-lookup/lookup.py
    srs-lookup/lookup.ps1
    update-claude-md/SKILL.md
    update-claude-md/generate.py
    verify-live/SKILL.md
    verify-live/scripts/audit_phases.py
  validation/
    RESULTS.md
    test_port.py
    check_preservation.py
    preservation-baseline.json
```

## Official documentation consulted

- [Copilot CLI](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli)
- [CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions)
- [CLI agent skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
- [CLI hooks](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks)
- [Hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)
- [Use custom agents](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli#use-custom-agents)
- [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- [Requested custom-agent documentation URL](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/customize-copilot-agents)
- [Current custom-agent creation page](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/create-custom-agents)
- [Custom-agent configuration reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration)

The requested custom-agent documentation URL returned an error during research;
the current creation page was reached through the official configuration reference.
Current docs support some cross-tool compatibility syntax, but this port deliberately
uses native camelCase events and fields. Installed CLI help/discovery were checked
as well as the docs; no compatibility of Claude configuration was presumed.
