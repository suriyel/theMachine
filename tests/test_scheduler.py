"""Tests for Scheduled Index Refresh (Feature #21).

Tests cover:
- scheduled_reindex_all: orchestrates periodic reindexing for active repos
- reindex_repo_task: per-repo Celery task with retry logic
- create_celery_app: Celery app factory with beat_schedule configuration

Security: N/A — internal Celery tasks, no user-facing input.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from celery.schedules import crontab


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo(
    status="active",
    indexed_branch=None,
    default_branch="main",
    name="test-repo",
):
    """Create a fake Repository-like object for testing."""
    repo = MagicMock()
    repo.id = uuid.uuid4()
    repo.name = name
    repo.url = f"https://github.com/test/{name}"
    repo.status = status
    repo.indexed_branch = indexed_branch
    repo.default_branch = default_branch
    repo.clone_path = f"/tmp/repos/{repo.id}"
    repo.last_indexed_at = None
    return repo


# ===========================================================================
# A — Happy Path Tests
# ===========================================================================


# [unit] — mocks DB and task enqueue
class TestScheduledReindexAllHappy:
    """A1: All active repos queued when no in-progress jobs."""

    def test_queues_all_active_repos(self):
        """A1: 3 active repos, no in-progress → queues 3."""
        from src.indexing.scheduler import scheduled_reindex_all

        repos = [_make_repo(name=f"repo-{i}") for i in range(3)]

        with (
            patch("src.indexing.scheduler._get_sync_session") as mock_session_fn,
            patch("src.indexing.scheduler.reindex_repo_task") as mock_task,
        ):
            session = MagicMock()
            mock_session_fn.return_value = session

            # active repos query
            active_query = MagicMock()
            # in-progress jobs query — empty
            in_progress_query = MagicMock()

            def _filter_side_effect(*args, **kwargs):
                return active_query

            def _query_side_effect(entity):
                q = MagicMock()
                # Distinguish between Repository and IndexJob queries
                from src.shared.models.index_job import IndexJob
                if entity is IndexJob.repo_id:
                    q.filter.return_value.distinct.return_value.all.return_value = []
                    return q
                else:
                    q.filter.return_value.all.return_value = repos
                    return q
                return q

            session.query.side_effect = _query_side_effect

            result = scheduled_reindex_all()

            assert result["queued"] == 3
            assert result["skipped"] == 0
            assert len(result["repos_queued"]) == 3
            assert mock_task.delay.call_count == 3

    def test_creates_index_job_for_repo(self):
        """A2: reindex_repo_task creates IndexJob with correct fields."""
        from src.indexing.scheduler import reindex_repo_task

        repo = _make_repo(indexed_branch="develop", default_branch="main")

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.first.return_value = repo

            # Capture the IndexJob added to session
            added_objects = []
            session.add.side_effect = lambda obj: added_objects.append(obj)

            # Mock the task binding so self.retry works
            task = reindex_repo_task
            result = task(str(repo.id))

            assert result["repo_id"] == str(repo.id)
            assert result["status"] == "pending"
            assert result["job_id"] is not None
            session.commit.assert_called_once()

    def test_uses_indexed_branch(self):
        """A3: Repo with indexed_branch='develop' → job branch='develop'."""
        from src.indexing.scheduler import reindex_repo_task

        repo = _make_repo(indexed_branch="develop", default_branch="main")

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.first.return_value = repo

            added_objects = []
            session.add.side_effect = lambda obj: added_objects.append(obj)

            result = reindex_repo_task(str(repo.id))

            assert len(added_objects) == 1
            job = added_objects[0]
            assert job.branch == "develop"

    def test_uses_default_branch_when_no_indexed(self):
        """A4: indexed_branch=None, default_branch='main' → branch='main'."""
        from src.indexing.scheduler import reindex_repo_task

        repo = _make_repo(indexed_branch=None, default_branch="main")

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.first.return_value = repo

            added_objects = []
            session.add.side_effect = lambda obj: added_objects.append(obj)

            reindex_repo_task(str(repo.id))

            job = added_objects[0]
            assert job.branch == "main"


# ===========================================================================
# B — Error Tests
# ===========================================================================


class TestReindexRepoTaskErrors:
    """B1-B4: Error handling in reindex_repo_task."""

    def test_retries_on_db_commit_failure(self):
        """B1: DB commit raises → task calls retry with countdown=3600."""
        from src.indexing.scheduler import reindex_repo_task

        repo = _make_repo()

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.first.return_value = repo
            session.commit.side_effect = Exception("DB connection lost")

            # Celery task retry mechanism
            with patch.object(
                reindex_repo_task, "retry", side_effect=Exception("retry")
            ) as mock_retry:
                with pytest.raises(Exception, match="retry"):
                    reindex_repo_task(str(repo.id))

                mock_retry.assert_called_once()
                call_kwargs = mock_retry.call_args
                assert call_kwargs.kwargs.get("countdown") == 3600
                assert call_kwargs.kwargs.get("max_retries") == 1

    def test_logs_error_on_retry_exhaustion(self, caplog):
        """B2: MaxRetriesExceededError → error logged, not propagated."""
        from celery.exceptions import MaxRetriesExceededError
        from src.indexing.scheduler import reindex_repo_task

        repo = _make_repo()

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.first.return_value = repo
            session.commit.side_effect = Exception("DB down")

            with patch.object(
                reindex_repo_task, "retry",
                side_effect=MaxRetriesExceededError("Max retries exceeded"),
            ):
                import logging
                with caplog.at_level(logging.ERROR):
                    result = reindex_repo_task(str(repo.id))

                assert result["status"] == "failed"
                assert "retry" in caplog.text.lower() or "exhausted" in caplog.text.lower()

    def test_skips_nonexistent_repo(self, caplog):
        """B3: Non-existent repo_id → returns skipped, logs warning."""
        from src.indexing.scheduler import reindex_repo_task

        fake_id = str(uuid.uuid4())

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.first.return_value = None

            import logging
            with caplog.at_level(logging.WARNING):
                result = reindex_repo_task(fake_id)

            assert result["status"] == "skipped"
            assert result["repo_id"] == fake_id
            assert result["job_id"] is None

    def test_skips_inactive_repo(self):
        """B4: Repo with status='pending' → returns skipped."""
        from src.indexing.scheduler import reindex_repo_task

        # Query filters by status='active', so inactive repo returns None
        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.first.return_value = None

            fake_id = str(uuid.uuid4())
            result = reindex_repo_task(fake_id)

            assert result["status"] == "skipped"


class TestCreateCeleryAppErrors:
    """B5: create_celery_app validation."""

    def test_raises_on_empty_broker_url(self):
        """B5: Empty broker_url → ValueError."""
        from src.indexing.celery_app import create_celery_app

        with pytest.raises(ValueError, match="broker_url"):
            create_celery_app("")


class TestScheduledReindexAllErrors:
    """B6: DB failure in scheduled_reindex_all."""

    def test_handles_db_failure_gracefully(self, caplog):
        """B6: DB unreachable → logs error, returns queued=0."""
        from sqlalchemy.exc import OperationalError
        from src.indexing.scheduler import scheduled_reindex_all

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.side_effect = OperationalError(
                "connection refused", {}, Exception()
            )

            import logging
            with caplog.at_level(logging.ERROR):
                result = scheduled_reindex_all()

            assert result["queued"] == 0
            assert result["skipped"] == 0
            assert "error" in result

    def test_handles_session_creation_failure(self, caplog):
        """B6b: _get_sync_session raises → logs error, returns with error."""
        from src.indexing.scheduler import scheduled_reindex_all

        with patch(
            "src.indexing.scheduler._get_sync_session",
            side_effect=Exception("Cannot create engine"),
        ):
            import logging
            with caplog.at_level(logging.ERROR):
                result = scheduled_reindex_all()

            assert result["queued"] == 0
            assert result["skipped"] == 0
            assert "error" in result
            assert "Cannot create engine" in result["error"]

    def test_handles_in_progress_query_failure(self, caplog):
        """B6c: In-progress jobs query fails → logs error, returns with error."""
        from src.indexing.scheduler import scheduled_reindex_all

        repos = [_make_repo(name="repo-x")]

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session

            call_count = [0]

            def _query_side_effect(entity):
                from src.shared.models.index_job import IndexJob
                q = MagicMock()
                if entity is IndexJob.repo_id:
                    q.filter.return_value.distinct.return_value.all.side_effect = (
                        Exception("in-progress query failed")
                    )
                    return q
                else:
                    q.filter.return_value.all.return_value = repos
                    return q

            session.query.side_effect = _query_side_effect

            import logging
            with caplog.at_level(logging.ERROR):
                result = scheduled_reindex_all()

            assert result["queued"] == 0
            assert result["skipped"] == 0
            assert "error" in result


# ===========================================================================
# C — Boundary Tests
# ===========================================================================


class TestBoundaryConditions:
    """C1-C4: Boundary conditions."""

    def test_no_active_repos(self, caplog):
        """C1: 0 active repos → queued=0, skipped=0."""
        from src.indexing.scheduler import scheduled_reindex_all

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.all.return_value = []

            import logging
            with caplog.at_level(logging.INFO):
                result = scheduled_reindex_all()

            assert result["queued"] == 0
            assert result["skipped"] == 0
            assert result["repos_queued"] == []

    def test_all_repos_in_progress(self):
        """C2: All active repos have in-progress jobs → queued=0, skipped=N."""
        from src.indexing.scheduler import scheduled_reindex_all

        repos = [_make_repo(name=f"repo-{i}") for i in range(3)]

        with (
            patch("src.indexing.scheduler._get_sync_session") as mock_session_fn,
            patch("src.indexing.scheduler.reindex_repo_task") as mock_task,
        ):
            session = MagicMock()
            mock_session_fn.return_value = session

            def _query_side_effect(entity):
                q = MagicMock()
                from src.shared.models.index_job import IndexJob
                if entity is IndexJob.repo_id:
                    # All repo IDs have in-progress jobs
                    q.filter.return_value.distinct.return_value.all.return_value = [
                        (r.id,) for r in repos
                    ]
                    return q
                else:
                    q.filter.return_value.all.return_value = repos
                    return q

            session.query.side_effect = _query_side_effect

            result = scheduled_reindex_all()

            assert result["queued"] == 0
            assert result["skipped"] == 3
            mock_task.delay.assert_not_called()

    def test_mixed_in_progress_and_eligible(self):
        """C3: 2 active repos, 1 in-progress → queues 1, skips 1."""
        from src.indexing.scheduler import scheduled_reindex_all

        repos = [_make_repo(name=f"repo-{i}") for i in range(2)]

        with (
            patch("src.indexing.scheduler._get_sync_session") as mock_session_fn,
            patch("src.indexing.scheduler.reindex_repo_task") as mock_task,
        ):
            session = MagicMock()
            mock_session_fn.return_value = session

            def _query_side_effect(entity):
                q = MagicMock()
                from src.shared.models.index_job import IndexJob
                if entity is IndexJob.repo_id:
                    # Only first repo has in-progress job
                    q.filter.return_value.distinct.return_value.all.return_value = [
                        (repos[0].id,)
                    ]
                    return q
                else:
                    q.filter.return_value.all.return_value = repos
                    return q

            session.query.side_effect = _query_side_effect

            result = scheduled_reindex_all()

            assert result["queued"] == 1
            assert result["skipped"] == 1
            mock_task.delay.assert_called_once_with(str(repos[1].id))

    def test_branch_fallback_to_main(self):
        """C4: Both branch fields None → falls back to 'main'."""
        from src.indexing.scheduler import reindex_repo_task

        repo = _make_repo(indexed_branch=None, default_branch=None)

        with patch("src.indexing.scheduler._get_sync_session") as mock_session_fn:
            session = MagicMock()
            mock_session_fn.return_value = session
            session.query.return_value.filter.return_value.first.return_value = repo

            added_objects = []
            session.add.side_effect = lambda obj: added_objects.append(obj)

            reindex_repo_task(str(repo.id))

            job = added_objects[0]
            assert job.branch == "main"


# ===========================================================================
# D — Config Tests
# ===========================================================================


class TestCeleryAppConfig:
    """D1-D3: Celery app configuration."""

    def test_custom_cron_schedule(self):
        """D1: Custom cron '0 4 * * *' → crontab(minute=0, hour=4)."""
        from src.indexing.celery_app import create_celery_app

        broker = "amqp://guest:guest@localhost:5672//"
        app = create_celery_app(broker, schedule_cron="0 4 * * *")

        # Verify broker is passed through
        assert app.conf.broker_url == broker

        schedule_entry = app.conf.beat_schedule["scheduled-reindex-all"]
        sched = schedule_entry["schedule"]
        assert isinstance(sched, crontab)
        # Verify the cron values
        assert 0 in sched.minute
        assert 4 in sched.hour

        # Verify task name is correct
        assert schedule_entry["task"] == "src.indexing.scheduler.scheduled_reindex_all"

    def test_default_cron_schedule(self):
        """D2: schedule_cron=None → default Sunday 02:00 UTC."""
        from src.indexing.celery_app import create_celery_app

        app = create_celery_app("amqp://guest:guest@localhost:5672//")

        schedule_entry = app.conf.beat_schedule["scheduled-reindex-all"]
        sched = schedule_entry["schedule"]
        assert isinstance(sched, crontab)
        assert 0 in sched.minute
        assert 2 in sched.hour
        assert 0 in sched.day_of_week  # Sunday = 0

        # Verify timezone
        assert app.conf.timezone == "UTC"

        # Verify task name
        assert schedule_entry["task"] == "src.indexing.scheduler.scheduled_reindex_all"

    def test_invalid_cron_raises_value_error(self):
        """D3: Invalid cron string → ValueError."""
        from src.indexing.celery_app import create_celery_app

        with pytest.raises(ValueError):
            create_celery_app(
                "amqp://guest:guest@localhost:5672//",
                schedule_cron="invalid",
            )

    def test_custom_cron_with_all_fields(self):
        """D4: Cron '30 6 15 3 2' uses all 5 fields correctly."""
        from src.indexing.celery_app import create_celery_app

        app = create_celery_app(
            "amqp://guest:guest@localhost:5672//",
            schedule_cron="30 6 15 3 2",
        )

        sched = app.conf.beat_schedule["scheduled-reindex-all"]["schedule"]
        assert 30 in sched.minute
        assert 6 in sched.hour
        assert 15 in sched.day_of_month
        assert 3 in sched.month_of_year
        assert 2 in sched.day_of_week  # Tuesday

    def test_cron_wildcard_handling(self):
        """D5: Wildcards are passed through (not filtered to specific values)."""
        from src.indexing.celery_app import create_celery_app

        # "0 4 * * *" — only minute and hour specified, rest are wildcards
        app = create_celery_app(
            "amqp://guest:guest@localhost:5672//",
            schedule_cron="0 4 * * *",
        )

        sched = app.conf.beat_schedule["scheduled-reindex-all"]["schedule"]
        # day_of_month, month_of_year, day_of_week should cover all values (wildcard)
        assert len(sched.day_of_month) > 1  # wildcard = all days
        assert len(sched.month_of_year) > 1  # wildcard = all months


# ===========================================================================
# Real Tests — RabbitMQ connectivity
# ===========================================================================


# ===========================================================================
# E — Module-Level App (DEF-002 fix)
# ===========================================================================


class TestModuleLevelCeleryApp:
    """E1-E3: Module-level Celery instance for CLI discovery (DEF-002)."""

    def test_module_has_app_attribute(self):
        """E1: celery_app module exposes 'app' attribute (Celery instance).

        celery -A src.indexing.celery_app worker requires a module-level
        Celery instance named 'app' or 'celery'. Without it, the CLI fails
        with 'has no attribute celery'.
        """
        import src.indexing.celery_app as mod

        assert hasattr(mod, "app"), (
            "celery_app module must export a module-level 'app' for "
            "'celery -A src.indexing.celery_app' CLI discovery"
        )
        from celery import Celery

        assert isinstance(mod.app, Celery), (
            f"celery_app.app must be a Celery instance, got {type(mod.app)}"
        )

    def test_module_app_has_beat_schedule(self):
        """E2: Module-level app has beat_schedule with scheduled-reindex-all."""
        import src.indexing.celery_app as mod

        schedule = mod.app.conf.beat_schedule
        assert "scheduled-reindex-all" in schedule, (
            "Module-level app must have 'scheduled-reindex-all' in beat_schedule"
        )
        entry = schedule["scheduled-reindex-all"]
        assert entry["task"] == "src.indexing.scheduler.scheduled_reindex_all"
        assert isinstance(entry["schedule"], crontab)

    def test_module_app_uses_env_broker_url(self):
        """E3: Module-level app reads CELERY_BROKER_URL from environment."""
        import os
        import src.indexing.celery_app as mod

        # The broker URL should come from CELERY_BROKER_URL or RABBITMQ_URL env
        expected_url = os.environ.get(
            "CELERY_BROKER_URL",
            os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"),
        )
        assert mod.app.conf.broker_url == expected_url, (
            f"Module-level app broker_url should be '{expected_url}', "
            f"got '{mod.app.conf.broker_url}'"
        )


@pytest.mark.real
class TestSchedulerReal:
    """[integration] — real RabbitMQ connectivity for Celery app (feature #21).

    Verifies that the Celery app can connect to the configured RabbitMQ broker.
    """

    def test_celery_app_connects_to_broker(self):
        """Real test: create Celery app and verify broker connection."""
        import os
        from src.indexing.celery_app import create_celery_app

        broker_url = os.environ.get(
            "RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"
        )
        app = create_celery_app(broker_url)

        # Verify the app is configured with correct broker
        assert app.conf.broker_url == broker_url
        assert "scheduled-reindex-all" in app.conf.beat_schedule

        # Verify we can establish a connection to RabbitMQ
        conn = app.connection()
        conn.ensure_connection(max_retries=3, timeout=5)
        conn.close()

    def test_celery_app_beat_schedule_structure(self):
        """Real test: verify beat_schedule entry has correct task reference."""
        import os
        from src.indexing.celery_app import create_celery_app

        broker_url = os.environ.get(
            "RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"
        )
        app = create_celery_app(broker_url)

        entry = app.conf.beat_schedule["scheduled-reindex-all"]
        assert entry["task"] == "src.indexing.scheduler.scheduled_reindex_all"
        assert isinstance(entry["schedule"], crontab)
