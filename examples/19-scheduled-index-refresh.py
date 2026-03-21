#!/usr/bin/env python3
"""Example: Scheduled Index Refresh (Feature #21).

Demonstrates how to create a Celery app with Beat schedule for periodic
repository reindexing, and how the scheduler tasks work.

Requirements:
    - RabbitMQ running on localhost:5672 (or set RABBITMQ_URL)
    - PostgreSQL running (or set DATABASE_URL)
"""

import os


def demo_celery_app_creation():
    """Create a Celery app with default and custom cron schedules."""
    from src.indexing.celery_app import create_celery_app

    broker_url = os.environ.get(
        "RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"
    )

    # Default schedule: Sunday 02:00 UTC
    app_default = create_celery_app(broker_url)
    schedule = app_default.conf.beat_schedule["scheduled-reindex-all"]
    print("Default schedule:")
    print(f"  Task: {schedule['task']}")
    print(f"  Cron: {schedule['schedule']}")
    print(f"  Timezone: {app_default.conf.timezone}")
    print()

    # Custom schedule: every day at 04:00 UTC
    app_custom = create_celery_app(broker_url, schedule_cron="0 4 * * *")
    custom_schedule = app_custom.conf.beat_schedule["scheduled-reindex-all"]
    print("Custom schedule (daily 04:00 UTC):")
    print(f"  Task: {custom_schedule['task']}")
    print(f"  Cron: {custom_schedule['schedule']}")
    print()


def demo_cron_parsing():
    """Show how cron strings are parsed into crontab kwargs."""
    from src.indexing.celery_app import _parse_cron_string

    examples = [
        "0 2 * * 0",       # Sunday 02:00
        "30 6 15 3 2",     # March 15, Tuesday, 06:30
        "0 */4 * * *",     # Every 4 hours
    ]

    for cron in examples:
        result = _parse_cron_string(cron)
        print(f"  '{cron}' -> {result}")


if __name__ == "__main__":
    print("=== Celery App Creation ===")
    demo_celery_app_creation()

    print("=== Cron String Parsing ===")
    demo_cron_parsing()

    print()
    print("To run the scheduler:")
    print("  celery -A src.indexing.celery_app beat --loglevel=info")
    print()
    print("To run the worker:")
    print("  celery -A src.indexing.celery_app worker --loglevel=info")
