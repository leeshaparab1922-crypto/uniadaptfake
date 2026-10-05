# ADR-0020: Duplicate-Topic similarity threshold 0.72 for BAAI/bge-m3

- **Status:** Accepted
- **Date:** 2026-10-05
- **Affects:** Phase 2 (FR-CUR-002 duplicate detection, FR-CUR-004 approval gate); Phase 3 Critic duplicate check must validate its own threshold
- **SRS refs:** FR-CUR-002 ("active versioned similarity/embedding-model configuration (initial threshold `>0.92`)"); Section 18 "Duplicate detection"; BUS-021; BUS-050; ADR-0015; plan decision P-7

## Context
- The SRS gives `0.92` as the *initial* duplicate threshold. BUS-050 and Section 18 require every threshold to be stored with its embedding-model version and validated before it is used. A changed value is a new configuration version.
- ADR-0015 chose `BAAI/bge-m3` (revision `5617a9f61b028005a4858fdac845db406aefb181`) and said the SRS starting values could not be assumed to suit it.
- Plan decision P-7 (human-approved 2026-10-04) set the validation bar: 60 labelled Topic pairs (`backend/tests/fixtures/duplicate_pairs.json`, 30 duplicates and 30 related-but-distinct), with **precision ≥ 0.90 and recall ≥ 0.80** at the strict `>` rule.

## Evidence (real bge-m3, 2026-10-05, run on this repo's pinned revision)
- Duplicate pairs scored 0.634–0.866 (median 0.804). Distinct pairs scored 0.326–0.930 (median 0.529). The highest-scoring distinct pair was "Perform breadth-first search" against "Perform depth-first search", at 0.930.
- At `0.92`: true positives 0, false positives 1, false negatives 30, so precision 0.00 and recall 0.00. **Fails.** Nothing at or above `0.75` passes. The largest is `0.74`, with precision 0.889 and recall 0.800.
- At `0.72`: true positives 27, false positives 3, false negatives 3, so precision 0.900 and recall 0.900. **Passes.**
- Below that, recall rises but precision falls under 0.90 (`0.70`: 0.875 / 0.933; `0.62`: 0.833 / 1.000).

## Decision
- The duplicate threshold for the bge-m3 embedding configuration is **`0.72`**, applied with the strict `>` rule.
- The value comes from `DUPLICATE_THRESHOLD_DEFAULT` (default `0.720`). It is created as a new DRAFT row, validated with `python -m scripts.validate_similarity_threshold --create-value 0.720 --activate`, and stored with its validation report, as BUS-050 requires.
- `0.92` remains documented as the SRS's initial value. It is no longer the configured default, because it fails validation for this model.

## Consequences
- `0.72` passes the P-7 bar exactly, with no margin. A change to the embedding model, its revision or the labelled set needs a new validation run, and a new threshold row and ADR if the value changes.
- At `0.72`, 3 of the 30 labelled distinct pairs would be flagged as duplicates, BFS/DFS among them. Duplicate flags only inform the Teacher, who can dismiss them; they do not block approval (plan "2B: As-built record"). So a false positive costs one Teacher review, not a wrong merge.
- Phase 3 (Critic duplicate check) and Phase 8 (Tutor grounding 0.70 and lockdown 0.85) thresholds are separate and must each be validated against bge-m3 in their own phases.
