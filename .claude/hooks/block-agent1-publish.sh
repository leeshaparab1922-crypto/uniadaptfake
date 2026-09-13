#!/usr/bin/env bash
# PreToolUse hook on Bash. Blocks git push / gh pr commands when invoked by
# the phase-planner-implementer subagent (Agent 1) — that agent must never
# publish; publishing is implementation-verifier-shipper's (Agent 2's) job,
# and only after a fresh human go-ahead in the main session.
#
# This is a backstop behind .claude/settings.json's permissions.deny rule
# (which applies session-wide) for the case where this hook is later reused
# or the deny rule is changed — belt-and-suspenders, not the only layer.
set -euo pipefail

INPUT="$(cat)"

# Extract agent_type and tool_input.command without requiring jq (not
# guaranteed installed on this machine — confirmed absent at build time).
AGENT_TYPE=$(python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('agent_type') or '')
except Exception:
    print('')
" <<< "$INPUT")

COMMAND=$(python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command') or '')
except Exception:
    print('')
" <<< "$INPUT")

# Only enforce for phase-planner-implementer; the main session and
# implementation-verifier-shipper are unaffected by this hook.
if [[ "$AGENT_TYPE" != "phase-planner-implementer" ]]; then
  exit 0
fi

# Case-insensitive match, tolerant of leading &&/;/whitespace and of the
# command appearing after other shell operators.
if echo "$COMMAND" | grep -Eiq '(^|[;&|[:space:]])git[[:space:]]+push([[:space:]]|$)'; then
  echo "Blocked: phase-planner-implementer must not run 'git push'. Publishing is implementation-verifier-shipper's responsibility, after human go-ahead." >&2
  exit 2
fi

if echo "$COMMAND" | grep -Eiq '(^|[;&|[:space:]])gh[[:space:]]+pr([[:space:]]|$)'; then
  echo "Blocked: phase-planner-implementer must not run 'gh pr ...'. Publishing is implementation-verifier-shipper's responsibility, after human go-ahead." >&2
  exit 2
fi

exit 0
