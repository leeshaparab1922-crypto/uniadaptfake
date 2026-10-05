"""Celery worker package. `celery -A app.workers worker` resolves `app` below."""

from app.workers.celery_app import celery_app

app = celery_app

__all__ = ["app", "celery_app"]
