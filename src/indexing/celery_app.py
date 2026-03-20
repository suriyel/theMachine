"""Celery configuration for code-context-retrieval."""

from celery import Celery
from celery.schedules import crontab

from src.query.config import settings


def create_celery_app() -> Celery:
    """Create and configure Celery application."""
    celery_app = Celery(
        "code_context_retrieval",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=[
            "src.indexing.tasks",
        ],
    )

    # Configure Celery
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour max
        task_soft_time_limit=3000,  # 50 minutes soft limit
    )

    # Beat schedule for weekly index refresh (Sundays at 2am)
    celery_app.conf.beat_schedule = {
        "weekly-index-refresh": {
            "task": "src.indexing.tasks.refresh_all_repositories",
            "schedule": crontab(hour=2, minute=0, day_of_week=0),
        },
    }

    return celery_app


# Create the Celery app instance
celery_app = create_celery_app()
