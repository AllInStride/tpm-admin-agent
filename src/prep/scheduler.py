"""APScheduler integration for periodic meeting prep scanning.

Provides scheduler setup, job management, and FastAPI lifespan
integration for the meeting prep system.
"""

from contextlib import asynccontextmanager
from datetime import UTC
from typing import TYPE_CHECKING

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = structlog.get_logger()

# Module-level scheduler instance
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance.

    Returns:
        AsyncIOScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=UTC)
    return _scheduler


def reset_scheduler() -> None:
    """Reset the scheduler instance (for testing)."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


@asynccontextmanager
async def prep_scheduler_lifespan() -> "AsyncGenerator[None, None]":
    """Lifespan context manager for prep scheduler.

    Starts the scheduler with a job to scan for upcoming meetings
    every 5 minutes. Shuts down cleanly on exit.

    Usage:
        async with prep_scheduler_lifespan():
            # Scheduler is running
            yield
        # Scheduler stopped
    """
    scheduler = get_scheduler()

    # Add meeting scanner job
    scheduler.add_job(
        scan_for_upcoming_meetings,
        "interval",
        minutes=5,
        id="meeting_prep_scanner",
        replace_existing=True,
        max_instances=1,  # Prevent overlap if job runs long
    )

    logger.info("Starting prep scheduler")
    scheduler.start()

    try:
        yield
    finally:
        logger.info("Shutting down prep scheduler")
        scheduler.shutdown(wait=False)


async def scan_for_upcoming_meetings() -> None:
    """Scheduled job: find meetings starting soon and send prep.

    Called every 5 minutes by the scheduler. Gets PrepService
    instance and runs scan_and_prepare.
    """
    from src.prep.prep_service import PrepService

    try:
        prep_service = PrepService.get_instance()
        results = await prep_service.scan_and_prepare()
        if results:
            logger.info("Sent meeting preps", count=len(results))
    except RuntimeError as e:
        # PrepService not initialized yet
        logger.warning("PrepService not ready", error=str(e))
    except Exception as e:
        logger.error("Prep scan failed", error=str(e))
