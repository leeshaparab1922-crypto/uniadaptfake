"""AI provider configuration, prompt registry, and agent-run log (SRS 31.3, ADR-0016/0017).

`prompt_versions` is append-only (ADR-0017): a database trigger rejects UPDATE/DELETE, so a
prompt that an `agent_runs` row points at can never change or disappear (NFR-DAT-002).
No secrets are stored here: the provider API key is read from the environment only.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

_PG = {"info": {"pg_only": True}}


def _enum(py_enum: type[enum.Enum], name: str, length: int) -> SAEnum:
    return SAEnum(py_enum, name=name, native_enum=False, create_constraint=True, length=length)


class AIProvider(str, enum.Enum):
    ANTHROPIC = "ANTHROPIC"
    OPENAI = "OPENAI"


class AgentRunStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REFUSED = "REFUSED"
    QUEUED_RETRY = "QUEUED_RETRY"


class AIProviderConfiguration(Base):
    """A versioned provider/model/effort/budget choice for one agent (no secrets)."""

    __tablename__ = "ai_provider_configurations"
    __table_args__ = (
        UniqueConstraint("agent", "config_version", name="uq_ai_provider_config_version"),
        Index(
            "uq_one_active_provider_config_per_agent",
            "agent",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        CheckConstraint("max_output_tokens > 0 AND token_budget > 0", name="ck_ai_provider_config_tokens"),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[AIProvider] = mapped_column(_enum(AIProvider, "ai_provider", 16), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    effort: Mapped[str] = mapped_column(String(16), nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    token_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("agent", "version", name="uq_prompt_version"),
        CheckConstraint("version >= 1", name="ck_prompt_versions_version"),
        _PG,
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"
    __table_args__ = (_PG,)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_provider_configurations.id", ondelete="RESTRICT"), nullable=False
    )
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # The FK to curriculum_versions is added in migration 0003 after both tables exist
    # (agent_runs <-> curriculum_versions reference each other).
    curriculum_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT", use_alter=True, name="fk_agent_runs_cv"),
        nullable=True,
    )
    input_refs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        _enum(AgentRunStatus, "agent_run_status", 16), nullable=False
    )
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
