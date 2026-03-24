"""Celery application factory with Beat schedule for periodic indexing."""

import logging
import os

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)


def _parse_cron_string(cron_str: str) -> dict:
    """Parse a cron string into kwargs for celery.schedules.crontab.

    Accepts standard 5-field cron format: "minute hour day_of_month month day_of_week"

    Args:
        cron_str: Cron expression string (5 fields).

    Returns:
        Dict with keys matching crontab() parameters.

    Raises:
        ValueError: If the cron string is not a valid 5-field expression.
    """
    parts = cron_str.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron string '{cron_str}': expected 5 fields "
            f"(minute hour day_of_month month day_of_week), got {len(parts)}"
        )

    field_names = ["minute", "hour", "day_of_month", "month_of_year", "day_of_week"]
    result = {}
    for name, value in zip(field_names, parts):
        if value != "*":
            result[name] = value
    return result


def create_celery_app(
    broker_url: str, schedule_cron: str | None = None
) -> Celery:
    """Create a Celery app with Beat schedule for periodic reindexing.

    Args:
        broker_url: AMQP broker URL for Celery.
        schedule_cron: Optional cron expression (5-field) for reindex schedule.
            Defaults to Sunday 02:00 UTC if None.

    Returns:
        Configured Celery application.

    Raises:
        ValueError: If broker_url is empty or cron string is invalid.
    """
    if not broker_url:
        raise ValueError("broker_url must not be empty")

    app = Celery(
        "indexing",
        broker=broker_url,
        include=["src.indexing.scheduler"],
    )

    if schedule_cron is not None:
        cron_kwargs = _parse_cron_string(schedule_cron)
    else:
        cron_kwargs = {"minute": 0, "hour": 2, "day_of_week": "sunday"}

    app.conf.beat_schedule = {
        "scheduled-reindex-all": {
            "task": "src.indexing.scheduler.scheduled_reindex_all",
            "schedule": crontab(**cron_kwargs),
        }
    }
    app.conf.timezone = "UTC"

    return app


# Module-level Celery instance for CLI discovery.
# Required by: celery -A src.indexing.celery_app worker/beat
app = create_celery_app(
    broker_url=os.environ.get(
        "CELERY_BROKER_URL",
        os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"),
    ),
    schedule_cron=os.environ.get("REINDEX_CRON"),
)
