#!/usr/bin/env bash
# Explicit bash invocation: executable file mode is not required.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  printf '%s\n' '{"permissionDecision":"deny","permissionDecisionReason":"Python 3 is required for the UniAdapt safety hook."}'
  exit 0
fi
"$PYTHON" -B "$SCRIPT_DIR/policy.py" publish
result=$?
if [[ $result -ne 0 ]]; then
  printf '%s\n' '{"permissionDecision":"deny","permissionDecisionReason":"UniAdapt safety hook could not run."}'
fi
exit 0
