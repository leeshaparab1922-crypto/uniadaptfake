"""Embedding configuration version (ADR-0015, BUS-050).

Every ContentChunk (and, in slice 2B, every Topic embedding) references the
configuration it was embedded with; similarity is only ever computed between
vectors that share the same `embedding_config_id`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

EMBEDDING_DIMENSION = 1024  # ADR-0015: BAAI/bge-m3 dense output.


class EmbeddingConfig(Base, TimestampMixin):
    __tablename__ = "embedding_configs"
    __table_args__ = (
        UniqueConstraint(
            "model_id",
            "model_revision",
            "dimension",
            "normalized",
            name="uq_embedding_config_identity",
        ),
        CheckConstraint("dimension = 1024", name="ck_embedding_configs_dimension"),
        {"info": {"pg_only": True}},
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    tokenizer_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    max_chunk_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_overlap_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
