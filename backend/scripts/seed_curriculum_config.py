"""Seeds slice 2B configuration: the active AI provider configuration (from deployment settings),
the synced prompt versions, the embedding configuration and its initial DRAFT duplicate threshold
(configured default 0.72, ADR-0020).

Idempotent. Run with: `python -m scripts.seed_curriculum_config` from `backend/`.
The threshold stays DRAFT until `python -m scripts.validate_similarity_threshold --activate` passes.
No API key is read or stored here.
"""

from __future__ import annotations

from app.db.session import SessionLocal
from app.prompts.registry import sync_prompts
from app.services import similarity_config_service as thresholds
from app.services.ai_config_service import ensure_active_config
from app.services.embedding_config_service import get_or_create_active_config


def main() -> None:
    with SessionLocal() as db:
        prompts = sync_prompts(db)
        print("Prompts:", ", ".join(f"{p.agent} v{p.version}" for p in prompts))
        cfg = ensure_active_config(db, "curriculum")
        print(f"AI config v{cfg.config_version}: {cfg.provider.value} {cfg.model} effort={cfg.effort}")
        emb = get_or_create_active_config(db)
        threshold = thresholds.resolve_threshold(db, emb)
        print(f"Duplicate threshold {threshold.value}: {threshold.status.value}")


if __name__ == "__main__":
    main()
