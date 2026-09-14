#!/usr/bin/env bash
# Fast lookup into the UniAdapt AI SRS without reading the whole 1527-line document.
# Usage: lookup.sh <QUERY>
#   QUERY forms:
#     FR-AUTH-001 | BUS-014 | AC-010          -> print that requirement's table row/block
#     "Section 43" | 43                        -> print the numbered section heading through
#                                                 the next numbered heading
#     phase 1 | phase-1                        -> print Section 43's row for that phase number
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SRS_FILE="$REPO_ROOT/SRS_Doc/UniAdapt_AI_Business_and_Software_Requirements_Specification.md"

if [[ ! -f "$SRS_FILE" ]]; then
  echo "ERROR: SRS file not found at $SRS_FILE" >&2
  exit 1
fi

QUERY="${1:-}"
if [[ -z "$QUERY" ]]; then
  echo "Usage: $0 <FR-ID|BUS-ID|AC-ID|section-number|'phase N'>" >&2
  exit 1
fi

# Case 1: an ID like FR-AUTH-001, BUS-014, AC-010, OBJ-001, NFR-SEC-004
if [[ "$QUERY" =~ ^(FR|BUS|AC|OBJ|BR|NFR|US)-[A-Z0-9-]+$ ]]; then
  # These IDs live inside pipe-delimited table rows. Print the matching row(s).
  MATCHES=$(grep -n "| $QUERY " "$SRS_FILE" || grep -n "$QUERY" "$SRS_FILE" || true)
  if [[ -z "$MATCHES" ]]; then
    echo "No match found for ID: $QUERY" >&2
    exit 1
  fi
  echo "$MATCHES"
  exit 0
fi

# Case 2: "phase N" or "phase-N" -> look inside Section 43's table for that phase row.
if [[ "$QUERY" =~ ^[Pp]hase[[:space:]_-]?([0-9]+)$ ]]; then
  PHASE_NUM="${BASH_REMATCH[1]}"
  START_LINE=$(grep -n '^## 43\. Project Phase Mapping' "$SRS_FILE" | cut -d: -f1)
  if [[ -z "$START_LINE" ]]; then
    echo "ERROR: Could not find Section 43 heading" >&2
    exit 1
  fi
  END_LINE=$(awk -v start="$START_LINE" 'NR>start && /^## [0-9]+\./{print NR; exit}' "$SRS_FILE")
  if [[ -z "$END_LINE" ]]; then
    END_LINE=$(wc -l < "$SRS_FILE")
  fi
  sed -n "${START_LINE},${END_LINE}p" "$SRS_FILE" | grep -E "^\| ${PHASE_NUM} " || \
    { echo "No Section 43 row found for phase $PHASE_NUM" >&2; exit 1; }
  exit 0
fi

# Case 3: a bare section number (e.g. "43" or "23") -> print that whole numbered section
# through (not including) the next numbered section heading.
if [[ "$QUERY" =~ ^[0-9]+$ ]]; then
  START_LINE=$(grep -n "^## ${QUERY}\. " "$SRS_FILE" | head -1 | cut -d: -f1)
  if [[ -z "$START_LINE" ]]; then
    echo "No section heading found for number: $QUERY" >&2
    exit 1
  fi
  END_LINE=$(awk -v start="$START_LINE" 'NR>start && /^## [0-9]+\./{print NR; exit}' "$SRS_FILE")
  if [[ -z "$END_LINE" ]]; then
    END_LINE=$(wc -l < "$SRS_FILE")
  else
    END_LINE=$((END_LINE - 1))
  fi
  sed -n "${START_LINE},${END_LINE}p" "$SRS_FILE"
  exit 0
fi

echo "Unrecognized query form: $QUERY" >&2
echo "Expected an ID (FR-*/BUS-*/AC-*/OBJ-*/BR-*/NFR-*/US-*), a section number, or 'phase N'." >&2
exit 1
