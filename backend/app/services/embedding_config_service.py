"""Resolve (or register) the active embedding configuration version (ADR-0015, BUS-050)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.embedding_config import EMBEDDING_DIMENSION, EmbeddingConfig


def get_or_create_active_config(db: Session) -> EmbeddingConfig:
    """The configuration named by deployment settings. Created on first use; the
    pinned revision hash is part of its identity, so changing model/revision
    always yields a new configuration version and never mutates an old one."""
    revision = settings.embedding_model_revision
    if not revision:
        raise ValueError("EMBEDDING_MODEL_REVISION must be pinned to a commit hash (ADR-0015).")
    config = db.scalar(
        select(EmbeddingConfig).where(
            EmbeddingConfig.model_id == settings.embedding_model_id,
            EmbeddingConfig.model_revision == revision,
            EmbeddingConfig.dimension == EMBEDDING_DIMENSION,
            EmbeddingConfig.normalized.is_(True),
        )
    )
    if config is None:
        config = EmbeddingConfig(
            model_id=settings.embedding_model_id,
            model_revision=revision,
            tokenizer_revision=revision,  # ADR-0015: tokenizer from the same revision
            dimension=EMBEDDING_DIMENSION,
            normalized=True,
            max_chunk_tokens=settings.chunk_max_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
        )
        db.add(config)
        db.commit()
    return config
