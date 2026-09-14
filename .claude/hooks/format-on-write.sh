#!/usr/bin/env bash
# PostToolUse hook on Edit|Write. Best-effort auto-fix/format of the
# just-written file using Ruff (Python, under backend/) or ESLint+Prettier
# (TS/TSX, under frontend/). Silently no-ops if the relevant directory,
# tool, or config does not exist yet (true until Phase 1 scaffolds them) —
# this hook must never fail the tool call or block on a missing tool.
set -uo pipefail  # no -e: every external command failure must be swallowed, not fatal

INPUT="$(cat)"

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

NORMALIZED=$(echo "$FILE_PATH" | tr "\\\\" "/")

case "$NORMALIZED" in
  */backend/*.py)
    if [[ -d "${CLAUDE_PROJECT_DIR}/backend" ]] && command -v ruff >/dev/null 2>&1; then
      ruff check --fix "$FILE_PATH" >/dev/null 2>&1 || true
      ruff format "$FILE_PATH" >/dev/null 2>&1 || true
    fi
    ;;
  */frontend/*.ts|*/frontend/*.tsx)
    if [[ -d "${CLAUDE_PROJECT_DIR}/frontend" ]] && [[ -f "${CLAUDE_PROJECT_DIR}/frontend/package.json" ]]; then
      if command -v npx >/dev/null 2>&1; then
        (cd "${CLAUDE_PROJECT_DIR}/frontend" && npx --no-install eslint --fix "$FILE_PATH") >/dev/null 2>&1 || true
        (cd "${CLAUDE_PROJECT_DIR}/frontend" && npx --no-install prettier --write "$FILE_PATH") >/dev/null 2>&1 || true
      fi
    fi
    ;;
esac

exit 0
