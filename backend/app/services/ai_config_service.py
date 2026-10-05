"""AI provider configuration versions (SRS 31.3 AIProviderConfiguration, ADR-0016).

Provider, model, effort and budgets come from deployment settings. Changing any of them creates a
NEW `config_version` (the previous one is deactivated, never edited), so every `agent_runs` row
keeps pointing at exactly the configuration it ran with. No secrets are stored.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai import AIProvider, AIProviderConfiguration


def ensure_active_config(db: Session, agent: str) -> AIProviderConfiguration:
    wanted = (
        AIProvider(settings.llm_provider.upper()),
        settings.llm_model,
        settings.llm_effort,
        settings.llm_max_output_tokens,
        settings.llm_token_budget,
    )
    active = db.scalar(
        select(AIProviderConfiguration).where(
            AIProviderConfiguration.agent == agent, AIProviderConfiguration.is_active.is_(True)
        )
    )
    if (
        active is not None
        and (
            active.provider,
            active.model,
            active.effort,
            active.max_output_tokens,
            active.token_budget,
        )
        == wanted
    ):
        return active
    next_version = (
        db.scalar(
            select(func.max(AIProviderConfiguration.config_version)).where(
                AIProviderConfiguration.agent == agent
            )
        )
        or 0
    ) + 1
    if active is not None:
        active.is_active = False
        db.flush()
    config = AIProviderConfiguration(
        agent=agent,
        provider=wanted[0],
        model=wanted[1],
        effort=wanted[2],
        max_output_tokens=wanted[3],
        token_budget=wanted[4],
        config_version=next_version,
        is_active=True,
    )
    db.add(config)
    db.commit()
    return config
