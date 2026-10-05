"""Acceptance rule for the duplicate-Topic threshold (ADR-0015, BUS-050, plan P-7).

Pure: given a labelled set of Topic pairs and their cosine similarities (computed elsewhere with
the real embedding model), decide whether a threshold is VALIDATED. The bar was approved on
2026-10-04: precision >= 0.90 AND recall >= 0.80 on `tests/fixtures/duplicate_pairs.json`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from decimal import Decimal

from app.services.curriculum_graph import is_duplicate

MIN_PRECISION = Decimal("0.90")
MIN_RECALL = Decimal("0.80")


@dataclass(frozen=True)
class LabelledSimilarity:
    similarity: float
    is_duplicate: bool  # ground truth label
    a: str = ""
    b: str = ""


@dataclass(frozen=True)
class ThresholdEvaluation:
    threshold: str
    pairs: int
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    precision: str
    recall: str
    min_precision: str
    min_recall: str
    passed: bool

    def as_report(self) -> dict:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> Decimal:
    # No predicted (or no actual) positives: the ratio is undefined and cannot satisfy the bar.
    return Decimal(0) if denominator == 0 else Decimal(numerator) / Decimal(denominator)


def evaluate_threshold(
    pairs: Sequence[LabelledSimilarity],
    threshold: Decimal | float | str,
    *,
    min_precision: Decimal = MIN_PRECISION,
    min_recall: Decimal = MIN_RECALL,
) -> ThresholdEvaluation:
    if not pairs:
        raise ValueError("the labelled set is empty")
    tp = fp = fn = tn = 0
    for p in pairs:
        predicted = is_duplicate(p.similarity, threshold)
        if predicted and p.is_duplicate:
            tp += 1
        elif predicted:
            fp += 1
        elif p.is_duplicate:
            fn += 1
        else:
            tn += 1
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    return ThresholdEvaluation(
        threshold=str(threshold),
        pairs=len(pairs),
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        true_negative=tn,
        precision=str(precision.quantize(Decimal("0.0001"))),
        recall=str(recall.quantize(Decimal("0.0001"))),
        min_precision=str(min_precision),
        min_recall=str(min_recall),
        passed=precision >= min_precision and recall >= min_recall,
    )
