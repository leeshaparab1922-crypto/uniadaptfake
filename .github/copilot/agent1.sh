#!/usr/bin/env bash
# A dedicated session restriction, NOT inferred Copilot agent identity.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export UNIADAPT_AGENT1_SESSION=1
exec copilot -C "$REPO_ROOT" --no-auto-update --agent=phase-planner-implementer \
  --disable-builtin-mcps --deny-tool='shell(git push)' --deny-tool='shell(gh pr:*)' \
  -i "${1:-Plan the next phase, then stop for human approval.}"
