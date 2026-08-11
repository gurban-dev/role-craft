"""Celery application."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "jaa",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_routes={
        "app.workers.tasks.submit_application_task": {"queue": "browser"},
    },
    beat_schedule={
        "daily-application-scheduler": {
            "task": "app.workers.tasks.daily_scheduler_task",
            "schedule": crontab(minute=0, hour="*/1"),
        },
        "retention-cleanup-daily": {
            "task": "app.workers.tasks.retention_cleanup_task",
            "schedule": crontab(minute=30, hour=3),
        },
    },
)
