"""Tests for prep scheduler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.prep.scheduler import (
    get_scheduler,
    prep_scheduler_lifespan,
    reset_scheduler,
    scan_for_upcoming_meetings,
)


class TestGetScheduler:
    """Tests for get_scheduler function."""

    def setup_method(self):
        """Reset scheduler before each test."""
        reset_scheduler()

    def teardown_method(self):
        """Reset scheduler after each test."""
        reset_scheduler()

    def test_returns_scheduler_instance(self):
        """get_scheduler returns AsyncIOScheduler instance."""
        scheduler = get_scheduler()
        assert scheduler is not None

    def test_returns_same_instance(self):
        """get_scheduler returns same instance on multiple calls."""
        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()
        assert scheduler1 is scheduler2

    def test_reset_clears_instance(self):
        """reset_scheduler clears the singleton."""
        scheduler1 = get_scheduler()
        reset_scheduler()
        scheduler2 = get_scheduler()
        assert scheduler1 is not scheduler2


class TestPrepSchedulerLifespan:
    """Tests for prep_scheduler_lifespan context manager."""

    def setup_method(self):
        """Reset scheduler before each test."""
        reset_scheduler()

    def teardown_method(self):
        """Reset scheduler after each test."""
        reset_scheduler()

    @pytest.mark.asyncio
    async def test_starts_scheduler(self):
        """prep_scheduler_lifespan starts the scheduler."""
        async with prep_scheduler_lifespan():
            scheduler = get_scheduler()
            assert scheduler.running is True

    @pytest.mark.asyncio
    async def test_adds_scanner_job(self):
        """prep_scheduler_lifespan adds meeting_prep_scanner job."""
        async with prep_scheduler_lifespan():
            scheduler = get_scheduler()
            jobs = scheduler.get_jobs()
            job_ids = [j.id for j in jobs]
            assert "meeting_prep_scanner" in job_ids

    @pytest.mark.asyncio
    async def test_job_has_5_minute_interval(self):
        """Scanner job runs every 5 minutes."""
        async with prep_scheduler_lifespan():
            scheduler = get_scheduler()
            job = scheduler.get_job("meeting_prep_scanner")
            assert job is not None
            # Check trigger is interval with 5 minutes
            trigger = job.trigger
            # APScheduler stores interval in seconds
            assert trigger.interval.total_seconds() == 300  # 5 minutes

    @pytest.mark.asyncio
    async def test_calls_shutdown_on_exit(self):
        """prep_scheduler_lifespan calls shutdown on exit."""
        with patch("src.prep.scheduler.AsyncIOScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler.running = True
            mock_scheduler_class.return_value = mock_scheduler

            # Reset to use new mock
            reset_scheduler()

            async with prep_scheduler_lifespan():
                pass

            # Verify shutdown was called
            mock_scheduler.shutdown.assert_called_once_with(wait=False)

    @pytest.mark.asyncio
    async def test_job_max_instances(self):
        """Scanner job has max_instances=1 to prevent overlap."""
        async with prep_scheduler_lifespan():
            scheduler = get_scheduler()
            job = scheduler.get_job("meeting_prep_scanner")
            assert job is not None
            assert job.max_instances == 1


class TestScanForUpcomingMeetings:
    """Tests for scan_for_upcoming_meetings function."""

    def setup_method(self):
        """Reset PrepService singleton before each test."""
        from src.prep.prep_service import PrepService

        PrepService.reset_instance()

    def teardown_method(self):
        """Reset PrepService singleton after each test."""
        from src.prep.prep_service import PrepService

        PrepService.reset_instance()

    @pytest.mark.asyncio
    async def test_calls_prep_service_scan(self):
        """scan_for_upcoming_meetings calls PrepService.scan_and_prepare."""
        from src.prep.prep_service import PrepService

        mock_service = MagicMock()
        mock_service.scan_and_prepare = AsyncMock(return_value=[])
        PrepService.set_instance(mock_service)

        await scan_for_upcoming_meetings()

        mock_service.scan_and_prepare.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_uninitialized_service(self):
        """scan_for_upcoming_meetings handles uninitialized PrepService."""
        # Don't set up PrepService
        # Should log warning but not raise
        await scan_for_upcoming_meetings()

    @pytest.mark.asyncio
    async def test_handles_scan_errors(self):
        """scan_for_upcoming_meetings handles errors gracefully."""
        from src.prep.prep_service import PrepService

        mock_service = MagicMock()
        mock_service.scan_and_prepare = AsyncMock(
            side_effect=Exception("Calendar API error")
        )
        PrepService.set_instance(mock_service)

        # Should not raise
        await scan_for_upcoming_meetings()

    @pytest.mark.asyncio
    async def test_logs_results(self):
        """scan_for_upcoming_meetings logs when preps are sent."""
        from src.prep.prep_service import PrepService

        mock_service = MagicMock()
        mock_service.scan_and_prepare = AsyncMock(
            return_value=[{"meeting_id": "event1"}]
        )
        PrepService.set_instance(mock_service)

        with patch("src.prep.scheduler.logger") as mock_logger:
            await scan_for_upcoming_meetings()
            mock_logger.info.assert_called_with("Sent meeting preps", count=1)
