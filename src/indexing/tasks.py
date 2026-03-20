"""Celery tasks for indexing operations."""

import asyncio
import logging
from uuid import UUID

from src.indexing.celery_app import celery_app
from src.shared.db.session import AsyncSessionLocal
from src.shared.services.repo_manager import RepoManager
from src.shared.models.index_job import TriggerType

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


@celery_app.task(bind=True, max_retries=3)
def refresh_all_repositories(self):
    """Scheduled task to refresh all registered repositories.

    This task runs periodically (default: weekly) to re-index
    all registered repositories.
    """
    logger.info("Starting scheduled index refresh for all repositories")

    async def _refresh():
        async with AsyncSessionLocal() as db:
            repo_manager = RepoManager(db)
            # Get all active repositories
            repositories = await repo_manager.list_all()

            if not repositories:
                logger.info("No repositories to refresh")
                return {"status": "success", "message": "No repositories to refresh"}

            # Queue indexing jobs for each repository
            results = []
            for repo in repositories:
                try:
                    if await repo_manager.has_active_job(repo.id):
                        results.append({"repo_id": str(repo.id), "status": "skipped", "reason": "active job exists"})
                        continue

                    job = await repo_manager.queue_indexing(repo.id, TriggerType.SCHEDULED)
                    await db.commit()
                    results.append({"repo_id": str(repo.id), "status": "queued", "job_id": str(job.id)})
                    logger.info(f"Queued indexing job for repository {repo.name}")
                except Exception as e:
                    logger.error(f"Failed to queue indexing for {repo.name}: {e}")
                    results.append({"repo_id": str(repo.id), "status": "error", "error": str(e)})

            success_count = sum(1 for r in results if r["status"] == "queued")
            error_count = sum(1 for r in results if r["status"] == "error")

            logger.info(f"Index refresh complete: {success_count} queued, {error_count} errors")

            return {
                "status": "success",
                "total": len(repositories),
                "queued": success_count,
                "errors": error_count,
            }

    try:
        return run_async(_refresh())
    except Exception as e:
        logger.error(f"Index refresh failed: {e}")
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@celery_app.task(bind=True)
def index_single_repository(self, repository_id: str):
    """Task to index a single repository.

    Args:
        repository_id: UUID of the repository to index
    """
    logger.info(f"Starting indexing for repository {repository_id}")

    async def _index():
        async with AsyncSessionLocal() as db:
            repo_manager = RepoManager(db)
            job = await repo_manager.queue_indexing(UUID(repository_id), TriggerType.MANUAL)
            await db.commit()
            return {
                "status": "success",
                "repository_id": repository_id,
                "job_id": str(job.id),
            }

    try:
        return run_async(_index())
    except Exception as e:
        logger.error(f"Failed to index repository {repository_id}: {e}")
        raise self.retry(exc=e, countdown=120)
