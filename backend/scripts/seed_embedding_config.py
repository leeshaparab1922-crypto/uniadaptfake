"""Registers the pinned embedding configuration (ADR-0015) in `embedding_configs`.

Idempotent. Run with: `python -m scripts.seed_embedding_config` from `backend/`.
"""

from __future__ import annotations

from app.db.session import SessionLocal
from app.services.embedding_config_service import get_or_create_active_config


def main() -> None:
    with SessionLocal() as db:
        config = get_or_create_active_config(db)
        print(
            f"Embedding config {config.id}: {config.model_id}@{config.model_revision} "
            f"dim={config.dimension} normalized={config.normalized}"
        )


if __name__ == "__main__":
    main()
