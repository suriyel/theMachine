"""Scheduled Index Refresh — Celery tasks for periodic repository reindexing."""

import logging
import os

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.shared.models.index_job import IndexJob
from src.shared.models.repository import Repository

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    """Create a synchronous SQLAlchemy session for Celery worker context.

    Returns:
        A new Session bound to the configured database.
    """
    database_url = os.environ.get("DATABASE_URL", "")
    # Convert async URL to sync if needed
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)
    return Session(engine)


@shared_task(bind=True, name="src.indexing.scheduler.reindex_repo_task")
def reindex_repo_task(self, repo_id: str) -> dict:
    """Reindex a single repository by creating an IndexJob record.

    Args:
        repo_id: UUID string of the repository to reindex.

    Returns:
        Dict with job_id, repo_id, and status.
    """
    session = _get_sync_session()
    try:
        repo = (
            session.query(Repository)
            .filter(Repository.id == repo_id, Repository.status == "active")
            .first()
        )

        if repo is None:
            logger.warning(
                "Repo %s not found or not active, skipping", repo_id
            )
            return {"job_id": None, "repo_id": repo_id, "status": "skipped"}

        branch = repo.indexed_branch or repo.default_branch or "main"

        try:
            job = IndexJob(repo_id=repo.id, branch=branch, status="pending")
            session.add(job)
            session.commit()
            logger.info(
                "Created reindex job %s for repo %s", job.id, repo.name
            )
            return {
                "job_id": str(job.id),
                "repo_id": repo_id,
                "status": "pending",
            }
        except Exception as exc:
            session.rollback()
            logger.error(
                "Failed to create reindex job for %s: %s", repo_id, exc
            )
            try:
                raise self.retry(exc=exc, countdown=3600, max_retries=1)
            except MaxRetriesExceededError:
                logger.error(
                    "Retry exhausted for repo %s, skipping until next window",
                    repo_id,
                )
                return {
                    "job_id": None,
                    "repo_id": repo_id,
                    "status": "failed",
                }
    finally:
        session.close()


@shared_task(bind=True, name="src.indexing.scheduler.scheduled_reindex_all")
def scheduled_reindex_all(self=None) -> dict:
    """Trigger reindexing for all active repositories.

    Queries all repositories with status='active', skips those with
    in-progress jobs (pending or running), and enqueues reindex_repo_task
    for each eligible repository.

    Returns:
        Dict with queued count, skipped count, and list of queued repo IDs.
    """
    try:
        session = _get_sync_session()
    except Exception as exc:
        logger.error("Failed to connect to database: %s", exc)
        return {"queued": 0, "skipped": 0, "error": str(exc)}

    try:
        try:
            active_repos = (
                session.query(Repository)
                .filter(Repository.status == "active")
                .all()
            )
        except Exception as exc:
            logger.error("Failed to query active repositories: %s", exc)
            return {"queued": 0, "skipped": 0, "error": str(exc)}

        if not active_repos:
            logger.info("No active repositories to reindex")
            return {"queued": 0, "skipped": 0, "repos_queued": []}

        # Find repos with in-progress jobs
        try:
            in_progress_rows = (
                session.query(IndexJob.repo_id)
                .filter(IndexJob.status.in_(["pending", "running"]))
                .distinct()
                .all()
            )
            in_progress_ids = {row[0] for row in in_progress_rows}
        except Exception as exc:
            logger.error("Failed to query in-progress jobs: %s", exc)
            return {"queued": 0, "skipped": 0, "error": str(exc)}

        queued = 0
        skipped = 0
        repos_queued = []

        for repo in active_repos:
            if repo.id in in_progress_ids:
                logger.info(
                    "Skipping %s — reindex already in progress", repo.name
                )
                skipped += 1
            else:
                reindex_repo_task.delay(str(repo.id))
                queued += 1
                repos_queued.append(str(repo.id))

        logger.info(
            "Scheduled reindex: queued=%d, skipped=%d", queued, skipped
        )
        return {
            "queued": queued,
            "skipped": skipped,
            "repos_queued": repos_queued,
        }
    finally:
        session.close()
