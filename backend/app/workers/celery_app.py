"""Celery application (Redis broker). `celery -A app.workers worker` loads this."""

from __future__ import annotations

from celery import Celery
from celery.signals import worker_init

from app.core.config import settings

celery_app = Celery(
    "uniadapt",
    broker=settings.effective_celery_broker_url,
    include=["app.workers.ingestion_tasks", "app.workers.curriculum_tasks"],
)
celery_app.conf.update(
    task_acks_late=True,  # a crashed worker's task is redelivered (resumable, BUS-040)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # long OCR/embedding tasks: do not hoard
    task_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    # Job limits (finding M5): the soft limit lets the task record a clear failure; the hard
    # limit kills a stuck worker. A killed job becomes retryable once stale (finding M2).
    task_soft_time_limit=settings.ingest_task_soft_time_limit_seconds,
    task_time_limit=settings.ingest_task_time_limit_seconds,
)


@worker_init.connect
def _sync_prompt_registry(**_kwargs: object) -> None:
    """ADR-0017: sync prompt files into `prompt_versions` when a worker starts; an edited-in-place
    prompt makes the worker refuse to start."""
    if not settings.prompt_sync_on_startup:
        return
    from app.db.session import SessionLocal
    from app.prompts.registry import sync_prompts

    with SessionLocal() as db:
        sync_prompts(db)
