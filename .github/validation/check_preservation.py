"""Read-only SHA-256 comparison; never resets/restores files or writes Git metadata."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASELINE = Path(__file__).with_name("preservation-baseline.json")


def main():
    expected = json.loads(BASELINE.read_text(encoding="utf-8"))["files"]
    failures = []
    for relative, digest in expected.items():
        file = ROOT / relative
        if not file.is_file():
            failures.append(f"MISSING: {relative}")
        elif hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            failures.append(f"CHANGED: {relative}")
    for file in ROOT.rglob("*"):
        if file.is_file():
            relative = file.relative_to(ROOT).as_posix()
            if not relative.startswith(".github/") and relative not in expected:
                failures.append(f"ADDED OUTSIDE .github: {relative}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"PASS: all {len(expected)} pre-existing files match SHA-256; no additions outside .github.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
