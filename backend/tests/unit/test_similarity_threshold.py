"""Duplicate-threshold acceptance rule (ADR-0015, BUS-050, plan P-7) and approval blocker."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.curriculum import ThresholdStatus
from app.services.similarity_config_service import NOT_VALIDATED_MESSAGE, threshold_blocker
from app.services.threshold_validation import LabelledSimilarity, evaluate_threshold

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "duplicate_pairs.json"


def labelled(tp: int, fp: int, fn: int, tn: int) -> list[LabelledSimilarity]:
    return (
        [LabelledSimilarity(0.97, True) for _ in range(tp)]
        + [LabelledSimilarity(0.95, False) for _ in range(fp)]
        + [LabelledSimilarity(0.60, True) for _ in range(fn)]
        + [LabelledSimilarity(0.30, False) for _ in range(tn)]
    )


def test_precision_and_recall_exactly_on_the_bar_pass():
    result = evaluate_threshold(labelled(tp=9, fp=1, fn=2, tn=10), Decimal("0.92"))
    # precision 9/10 = 0.90 and recall 9/11 = 0.818
    assert (result.true_positive, result.false_positive, result.false_negative, result.true_negative) == (
        9,
        1,
        2,
        10,
    )
    assert result.precision == "0.9000" and result.passed is True


def test_precision_just_below_the_bar_fails():
    assert (
        evaluate_threshold(labelled(tp=8, fp=1, fn=0, tn=5), Decimal("0.92")).passed is False
    )  # 8/9 = 0.889


def test_recall_just_below_the_bar_fails():
    result = evaluate_threshold(labelled(tp=3, fp=0, fn=1, tn=3), Decimal("0.92"))  # recall 0.75
    assert result.recall == "0.7500" and result.passed is False
    assert evaluate_threshold(labelled(tp=4, fp=0, fn=1, tn=3), Decimal("0.92")).passed is True  # recall 0.80


def test_similarity_equal_to_threshold_is_not_a_predicted_duplicate():
    pairs = [LabelledSimilarity(0.92, True), LabelledSimilarity(0.99, True)]
    result = evaluate_threshold(pairs, Decimal("0.92"))
    assert result.true_positive == 1 and result.false_negative == 1


def test_no_predicted_positives_cannot_pass():
    result = evaluate_threshold(
        [LabelledSimilarity(0.5, True), LabelledSimilarity(0.4, False)], Decimal("0.92")
    )
    assert result.passed is False and result.precision == "0.0000"


def test_empty_set_is_an_error():
    with pytest.raises(ValueError):
        evaluate_threshold([], Decimal("0.92"))


def test_report_is_json_serialisable_and_records_the_bar():
    report = evaluate_threshold(labelled(9, 1, 2, 10), "0.920").as_report()
    json.dumps(report)
    assert report["min_precision"] == "0.90" and report["min_recall"] == "0.80"


def test_labelled_fixture_has_about_sixty_balanced_pairs():
    pairs = json.loads(FIXTURE.read_text(encoding="utf-8"))["pairs"]
    assert len(pairs) == 60
    assert sum(p["duplicate"] for p in pairs) == 30
    assert all(p["a"] and p["b"] and p["a"] != p["b"] for p in pairs)


def test_blocker_unless_threshold_is_active_for_the_same_embedding_config():
    cfg = uuid.uuid4()
    active = SimpleNamespace(status=ThresholdStatus.ACTIVE, embedding_config_id=cfg)
    assert threshold_blocker(active, cfg) is None
    assert threshold_blocker(active, uuid.uuid4()) == NOT_VALIDATED_MESSAGE  # model changed
    assert threshold_blocker(None, cfg) == NOT_VALIDATED_MESSAGE
    for status in (ThresholdStatus.DRAFT, ThresholdStatus.VALIDATED, ThresholdStatus.RETIRED):
        assert threshold_blocker(SimpleNamespace(status=status, embedding_config_id=cfg), cfg)
