#!/usr/bin/env bash
# PreToolUse hook on Edit|Write. Blocks any edit/write targeting SRS_Doc/** —
# that directory is the project's single source-of-truth specification and
# must never be modified by any agent (or the main session acting as one).
# Humans who need to amend the SRS should do so directly, outside Claude
# Code tool calls, so the change is an explicit, deliberate act.
#
# Unlike block-agent1-publish.sh, this hook is deliberately NOT agent-scoped
# — no agent, and no session, should ever write to SRS_Doc/.
set -euo pipefail

INPUT="$(cat)"

# Extract tool_input.file_path without requiring jq (not guaranteed
# installed on this machine — matches the convention in
# block-agent1-publish.sh).
FILE_PATH=$(python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path') or '')
except Exception:
    print('')
" <<< "$INPUT")

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Normalize case and slashes so this catches SRS_Doc, srs_doc, absolute
# paths, and Windows-style backslashes alike.
NORMALIZED=$(echo "$FILE_PATH" | tr "A-Z" "a-z" | tr "\\\\" "/")

if echo "$NORMALIZED" | grep -Eq "(^|/)srs_doc/"; then
  echo "Blocked: SRS_Doc/ is the source-of-truth spec and must never be edited by any agent." >&2
  exit 2
fi

exit 0
