#!/usr/bin/env bash
# Explicit bash invocation: executable file mode is not required.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  printf '{}\n'
  exit 0
fi
"$PYTHON" -B "$SCRIPT_DIR/policy.py" format
result=$?
if [[ $result -ne 0 ]]; then
  printf '{}\n'
fi
exit 0
