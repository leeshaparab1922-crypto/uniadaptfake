"""Validates the duplicate-Topic threshold with the REAL embedding model (ADR-0015, plan P-7).

Embeds the ~60 labelled pairs in `tests/fixtures/duplicate_pairs.json` with bge-m3, evaluates the
current threshold (default: the threshold row for the active embedding configuration), stores the
report in `similarity_thresholds.validation_report`, and marks the row VALIDATED only when
precision >= 0.90 and recall >= 0.80. A failing run leaves it DRAFT; a different value is then a
NEW human-approved threshold row (`--create-value 0.90`), never an edit.

Run from `backend/`:
  python -m scripts.validate_similarity_threshold            # evaluate + record
  python -m scripts.validate_similarity_threshold --activate  # also activate when it passes
  python -m scripts.validate_similarity_threshold --create-value 0.90   # new DRAFT row first
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.session import SessionLocal
from app.integrations.embedding import BgeM3Embedder
from app.services import similarity_config_service as thresholds
from app.services.curriculum_graph import cosine_similarity
from app.services.curriculum_service import topic_text
from app.services.embedding_config_service import get_or_create_active_config
from app.services.threshold_validation import LabelledSimilarity, evaluate_threshold

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "duplicate_pairs.json"


def load_pairs(path: Path = FIXTURE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["pairs"]


def _as_topic_text(label: str) -> str:
    name, _, outcome = label.partition(": ")
    return topic_text(name, [outcome] if outcome else [name])


def similarities(embedder: BgeM3Embedder, pairs: list[dict]) -> list[LabelledSimilarity]:
    texts = [_as_topic_text(p[side]) for p in pairs for side in ("a", "b")]
    vectors = embedder.embed(texts)
    result = []
    for i, p in enumerate(pairs):
        sim = cosine_similarity(vectors[2 * i], vectors[2 * i + 1])
        result.append(LabelledSimilarity(sim, bool(p["duplicate"]), p["a"], p["b"]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--activate", action="store_true", help="activate the threshold when it passes")
    parser.add_argument("--create-value", help="create a new DRAFT threshold row with this value first")
    args = parser.parse_args()

    embedder = BgeM3Embedder()
    with SessionLocal() as db:
        config = get_or_create_active_config(db)
        if args.create_value:
            row = thresholds.create_draft_threshold(db, config, value=args.create_value)
            db.commit()
        else:
            row = thresholds.resolve_threshold(db, config)
        labelled = similarities(embedder, load_pairs())
        evaluation = evaluate_threshold(labelled, row.value)
        report = {
            **evaluation.as_report(),
            "embedding_config_id": str(config.id),
            "model_id": config.model_id,
            "model_revision": config.model_revision,
            "fixture": FIXTURE.name,
            "misclassified": [
                {"a": p.a, "b": p.b, "similarity": p.similarity, "label_duplicate": p.is_duplicate}
                for p in labelled
                if (p.similarity > float(row.value)) != p.is_duplicate
            ],
        }
        row = thresholds.record_validation(db, row.id, report=report, passed=evaluation.passed)
        print(json.dumps({k: v for k, v in report.items() if k != "misclassified"}, indent=2))
        print(f"Threshold {row.id} value={row.value} -> {row.status.value}")
        if evaluation.passed and args.activate:
            row = thresholds.activate_threshold(db, row.id)
            print("Threshold activated.")
        elif not evaluation.passed:
            raise SystemExit(
                "Validation FAILED: the threshold stays DRAFT and curriculum cannot be approved. "
                "Review the misclassified pairs; a different value needs a new human-approved row."
            )


if __name__ == "__main__":
    main()
