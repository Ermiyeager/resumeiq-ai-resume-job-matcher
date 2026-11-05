"""Celery worker entry point.

    celery -A app.celery_app worker --loglevel=info
"""

from __future__ import annotations

from celery import Celery

from .db import init_engine
from .settings import settings
from .tasks import run_analysis

celery = Celery("resumeiq", broker=settings.celery_broker_url)
celery.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, task_time_limit=120)

init_engine()


@celery.task(name="resumeiq.run_analysis", max_retries=0)
def run_analysis_task(analysis_id: str) -> None:
    run_analysis(analysis_id)
