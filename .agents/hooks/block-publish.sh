#!/usr/bin/env bash
# PreToolUse hook: prompts user for approval on git push / gh pr commands.
#
# AGY contract:
#   stdin  = JSON with { "toolCall": { "name": "...", "args": { "CommandLine": "..." } }, ... }
#   stdout = JSON with { "decision": "allow"|"deny"|"ask"|"force_ask", "reason": "..." }
#
# Prompts user confirmation for git push / gh pr commands.
set -euo pipefail

INPUT="$(cat)"

COMMAND=$(python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('toolCall', {}).get('args', {}).get('CommandLine') or '')
except Exception:
    print('')
" <<< "$INPUT")

if echo "$COMMAND" | grep -Eiq '(^|[;&|[:space:]])git[[:space:]]+push([[:space:]]|$)'; then
  echo '{"decision":"ask","reason":"git push detected. Only approve if implementation-verifier-shipper is active and you have granted explicit approval to ship."}'
  exit 0
fi

if echo "$COMMAND" | grep -Eiq '(^|[;&|[:space:]])gh[[:space:]]+pr([[:space:]]|$)'; then
  echo '{"decision":"ask","reason":"gh pr detected. Only approve if implementation-verifier-shipper is active and you have granted explicit approval to ship."}'
  exit 0
fi

# All other commands: allow silently
echo '{"decision":"allow"}'
exit 0
