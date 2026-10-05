"""P-7: the labelled set meets the acceptance bar with the REAL bge-m3 model. Marker: hf_model."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.hf_model


def test_labelled_set_meets_acceptance_criteria():
    from decimal import Decimal

    from app.core.config import settings
    from app.integrations.embedding import BgeM3Embedder
    from app.services.threshold_validation import evaluate_threshold
    from scripts.validate_similarity_threshold import load_pairs, similarities

    threshold = Decimal(settings.duplicate_threshold_default)  # ADR-0020: 0.72 for bge-m3
    result = evaluate_threshold(similarities(BgeM3Embedder(), load_pairs()), threshold)
    assert result.passed, result.as_report()
