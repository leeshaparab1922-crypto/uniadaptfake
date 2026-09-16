# Copilot port validation — 2026-09-16

Result: **27 test methods passed**, with parameterized path/command cases and
22 real hook-wrapper fixture invocations (11 each through Bash and PowerShell).
All four skills passed the installed skill-creator frontmatter validator.
All 220 pre-existing repository files, including Git metadata, matched the
pre-creation SHA-256 snapshot. This is adapter validation, not a live Copilot
agent/application/shipping certification.

## Environment and discovery

- `copilot --version`: GitHub Copilot CLI 1.0.85.
- `copilot --help`, `copilot help commands`, `copilot help permissions`:
  confirmed `--agent`, `/agent [name]`, skill/instruction inspection and CLI
  tool-denial patterns. No model session was started by these commands.
- `copilot --no-auto-update skill list --json`: all four same-named ported skills
  resolve to `.github/skills`. The pre-existing distinct update-agents-md skill
  remains visible under `.agents`; nothing was disabled or edited there.
- `copilot --no-auto-update instruction list --json`: repository instructions and
  all four modular rules discovered; backend/frontend/services/SRS scopes match
  the intended `applyTo` values. Existing AGENTS.md and CLAUDE.md also discovered.
- Bash: Git for Windows Bash 5.2.37 at `C:/Program Files/Git/bin/bash.exe`.
  The system Bash launcher was not substituted for Git Bash in fixture tests.
- PowerShell: installed `pwsh` 7; parser and wrapper execution passed.
- Python: installed Python 3.14; helpers use Python 3.11-compatible standard
  library code. PyYAML was already available and was used without installation.

## Commands executed and results

```powershell
python -B .github/validation/test_port.py
python -B .github/validation/check_preservation.py

Get-ChildItem .github/skills -Directory | ForEach-Object {
    python -B C:/Users/parab/.codex/skills/.system/skill-creator/scripts/quick_validate.py $_.FullName
}

python -B .github/skills/phase-status/check.py
python -B .github/skills/verify-live/scripts/audit_phases.py

copilot --no-auto-update skill list --json
copilot --no-auto-update instruction list --json

rg -l 'SRS_Doc|git push|gh pr|phase-planner-implementer|implementation-verifier-shipper|human approval|phase.state|traceability' .github/agents .github/instructions .github/skills .github/copilot-instructions.md
git --no-optional-locks status --short
git --no-optional-locks diff --name-only
git --no-optional-locks diff -- .claude AGENTS.md CLAUDE.md docs SRS_Doc
```

The test suite ended `Ran 27 tests ... OK`, no skips. The first development run
had one incorrect test expectation for lookup: an ID can match multiple SRS rows.
That expectation was corrected to match the original lookup's intentional
behavior. Subsequent runs, including the final command-substitution cases, passed.

`phase-status` returned 0, all nine phases not_started, no false application
deliverables. The no-argument static audit returned 0 with nothing claimed done.
These read existing state without modifying or regenerating it. The four skill
validator invocations each printed `Skill is valid!`.

A search for both Claude project/skill directory variables and the old argument
placeholder in runtime files found no unresolved occurrences. Native agent/skill
frontmatter contains no Claude model, permissionMode, maxTurns, color, shell or
skill-preload keys. The unsupported names that appear in validation code are
intentional rejection checks, not configuration.

## Detailed coverage

| Check | Result |
| --- | --- |
| Component inventory | Both agents, four complete rules, four skills and all four source helpers, native hooks, all six hook wrappers, shared policy, instructions, docs and validation exist |
| Hook JSON | Parsed; version 1, correct event names, command fields, cwd, positive timeouts, every script reference exists |
| YAML/frontmatter | Parsed using existing PyYAML; skill names/descriptions, agent fields and instruction applyTo checked |
| Python syntax | AST parsed for all seven new Python files; no compilation cache |
| Bash syntax | `bash -n` passed for all five new/copied Bash scripts |
| PowerShell syntax | ParseFile passed for all five PowerShell scripts |
| SRS protection | Relative, absolute, nested, drive, UNC, mixed case/slashes, directory targets, traversal, trailing-dot/space and ADS cases deny |
| File-tool adapters | create/edit/str_replace/str_replace_editor, encoded args, multi-edit, patch Add/Update/Delete/Move, move/delete tested |
| Malformed writes | Missing/invalid path, absent/malformed args, broken JSON and unknown mutation schema fail closed |
| Non-SRS paths | Backend/frontend targets allowed through SRS protection; similar names and documentation content do not falsely block |
| Read-only paths | view and str_replace_editor view, Get-Content SRS reads remain allowed |
| Shell SRS writes | Redirection, Set-Content, deletion, git restore/checkout, protected cwd deny |
| Agent 1 session publication | git push and gh pr create/merge/list deny under launcher marker, including joined commands, options, executable paths, nested shells and simple substitutions |
| Missing identity/main session | Same publishing commands return ask, not an Agent 1 denial; invented payload identity is ignored |
| Publishing alternatives | send-pack, package/container publish, GH API mutation and other listed variants recognized |
| Literal documentation | echo/printf/Write-Output mentions remain ordinary, including quoted operator/substitution text |
| Opaque commands | Interpreters, aliases, scripts, variable expansion and unknown commands require review |
| Format no-op | Missing app directories/tools and malformed payloads return success with empty decision; no app writes |
| Formatter scope | Mocked Ruff and local Node/ESLint/Prettier calls target only the written file; unrelated/outside-repo files stay unchanged |
| Formatter failures | OSError and non-success tool results handled without invalidating the original write |
| Wrapper protocol | Both platforms emit parseable Copilot JSON, reasons for denials, exit 0, and work from a nested cwd |
| Lookup parity | 12 success/failure query cases compared between Bash/Python from nested cwd; PowerShell phase query passed |
| Generator | Isolated create/replace/append fixtures preserve surrounding authored text; root CLAUDE.md never generated |
| Static audit | Empty state exit 0, missing evidence exit 1, present evidence/PASS exit 0; scaffolding excluded |
| Preservation | All 220 original SHA-256 hashes match; no additions outside .github |

The suite creates and removes its own temporary fixture directories under
`.github/validation`. It never tests formatting on real application files, never
runs original `.claude` scripts, and never runs the generator against the real
root. Native formatters are mocked when verifying command selection; no external
formatter package was installed or invoked on application source.

## Remaining gaps and preservation proof

Native hook payloads expose no reliable active-agent identity. Tests prove a
dedicated session marker, not native agent-scoped enforcement. Fresh human
approval, exact formula correctness, reviewer independence and verifier write
scope are preserved instructions, not authenticated by the hook. No claim of
full enforcement equivalence is made. Simple path normalization is tested;
cross-platform symlink/junction attacks and arbitrary executable behavior are not
certified. Timeout fail-open behavior belongs to Copilot and cannot be removed
by this adapter.

The CLI's live hook loader was not invoked in a model-driven session. In
particular, co-loaded legacy `.claude/settings.json` behavior remains unverified;
see the README's coexistence section. Live browser/application checks, actual
formatter execution, reviewer invocation, and branch/commit/push/PR operations
were intentionally not performed as part of this configuration-only task.

Final Git observations: `status --short` shows only `?? .github/`; both diff
commands above are empty. `check_preservation.py` reports:

```text
PASS: all 220 pre-existing files match SHA-256; no additions outside .github.
```

`.claude/**`, AGENTS.md, CLAUDE.md, docs, SRS_Doc and Git metadata are unchanged.
No existing file was modified. No dependencies were installed, no commit was
created, no push was performed, and no pull request was created.

The baseline is a task-specific preservation record, not a permanent CI assertion
that future authorized application work must leave these files unchanged. It
contains hashes only and never restores or overwrites user files.
