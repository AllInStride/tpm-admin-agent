"""Tests for PrepService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.prep.context_gatherer import PrepContext
from src.prep.prep_service import PrepService
from src.prep.schemas import PrepConfig


@pytest.fixture
def mock_calendar_adapter():
    """Create mock CalendarAdapter."""
    adapter = MagicMock()
    adapter.list_upcoming_events = AsyncMock(return_value=[])
    return adapter


@pytest.fixture
def mock_slack_adapter():
    """Create mock SlackAdapter."""
    adapter = MagicMock()
    adapter.lookup_user_by_email = AsyncMock(return_value=None)
    adapter.send_prep_dm = AsyncMock(return_value={"success": True, "ts": "123"})
    return adapter


@pytest.fixture
def mock_item_matcher():
    """Create mock ItemMatcher."""
    matcher = MagicMock()
    matcher.get_items_for_prep = AsyncMock(return_value=[])
    return matcher


@pytest.fixture
def mock_context_gatherer():
    """Create mock ContextGatherer."""
    gatherer = MagicMock()
    gatherer.gather_for_meeting = AsyncMock(
        return_value=PrepContext(
            open_items=[],
            related_docs=[],
            slack_highlights=[],
            previous_meeting=None,
        )
    )
    return gatherer


@pytest.fixture
def prep_service(
    mock_calendar_adapter,
    mock_slack_adapter,
    mock_item_matcher,
    mock_context_gatherer,
):
    """Create PrepService with mocked dependencies."""
    service = PrepService(
        calendar_adapter=mock_calendar_adapter,
        slack_adapter=mock_slack_adapter,
        item_matcher=mock_item_matcher,
        context_gatherer=mock_context_gatherer,
    )
    return service


class TestPrepServiceSingleton:
    """Tests for PrepService singleton pattern."""

    def setup_method(self):
        """Reset singleton before each test."""
        PrepService.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        PrepService.reset_instance()

    def test_get_instance_raises_when_not_set(self):
        """get_instance raises RuntimeError when not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            PrepService.get_instance()

    def test_set_and_get_instance(self, prep_service):
        """set_instance and get_instance work correctly."""
        PrepService.set_instance(prep_service)
        assert PrepService.get_instance() is prep_service

    def test_reset_instance(self, prep_service):
        """reset_instance clears the singleton."""
        PrepService.set_instance(prep_service)
        PrepService.reset_instance()
        with pytest.raises(RuntimeError):
            PrepService.get_instance()


class TestScanAndPrepare:
    """Tests for scan_and_prepare method."""

    def setup_method(self):
        """Reset singleton before each test."""
        PrepService.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        PrepService.reset_instance()

    @pytest.mark.asyncio
    async def test_calls_calendar_with_time_window(
        self,
        prep_service,
        mock_calendar_adapter,
    ):
        """scan_and_prepare calls calendar with correct time window."""
        await prep_service.scan_and_prepare(calendar_id="test@example.com")

        mock_calendar_adapter.list_upcoming_events.assert_called_once()
        call_kwargs = mock_calendar_adapter.list_upcoming_events.call_args.kwargs

        assert call_kwargs["calendar_id"] == "test@example.com"

        # Check time window is approximately correct (lead_time to lead_time + 5min)
        time_min = call_kwargs["time_min"]
        time_max = call_kwargs["time_max"]
        assert isinstance(time_min, datetime)
        assert isinstance(time_max, datetime)
        # Window should be ~5 minutes
        delta = (time_max - time_min).total_seconds()
        assert 290 <= delta <= 310  # ~5 minutes

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_meetings(
        self,
        prep_service,
        mock_calendar_adapter,
    ):
        """scan_and_prepare returns empty list when no meetings."""
        mock_calendar_adapter.list_upcoming_events.return_value = []

        results = await prep_service.scan_and_prepare()

        assert results == []

    @pytest.mark.asyncio
    async def test_prepares_found_meetings(
        self,
        prep_service,
        mock_calendar_adapter,
        mock_context_gatherer,
        mock_slack_adapter,
    ):
        """scan_and_prepare prepares each found meeting."""
        now = datetime.now(UTC)
        mock_calendar_adapter.list_upcoming_events.return_value = [
            {
                "id": "event1",
                "summary": "Team Sync",
                "start": {"dateTime": (now + timedelta(minutes=10)).isoformat()},
                "end": {"dateTime": (now + timedelta(minutes=70)).isoformat()},
                "attendees": [],
            },
        ]

        results = await prep_service.scan_and_prepare()

        assert len(results) == 1
        assert results[0]["meeting_id"] == "event1"
        mock_context_gatherer.gather_for_meeting.assert_called_once()

    @pytest.mark.asyncio
    async def test_prevents_duplicate_preps(
        self,
        prep_service,
        mock_calendar_adapter,
        mock_context_gatherer,
    ):
        """scan_and_prepare skips already prepped meetings."""
        now = datetime.now(UTC)
        event = {
            "id": "event1",
            "summary": "Team Sync",
            "start": {"dateTime": (now + timedelta(minutes=10)).isoformat()},
            "end": {"dateTime": (now + timedelta(minutes=70)).isoformat()},
            "attendees": [],
        }
        mock_calendar_adapter.list_upcoming_events.return_value = [event]

        # First scan
        results1 = await prep_service.scan_and_prepare()
        assert len(results1) == 1

        # Second scan - same meeting
        results2 = await prep_service.scan_and_prepare()
        assert len(results2) == 0

        # gather_for_meeting only called once
        assert mock_context_gatherer.gather_for_meeting.call_count == 1

    @pytest.mark.asyncio
    async def test_handles_scan_error_gracefully(
        self,
        prep_service,
        mock_calendar_adapter,
    ):
        """scan_and_prepare handles calendar errors gracefully."""
        mock_calendar_adapter.list_upcoming_events.side_effect = Exception("API Error")

        # Should raise the exception (not swallow it)
        with pytest.raises(Exception, match="API Error"):
            await prep_service.scan_and_prepare()

    @pytest.mark.asyncio
    async def test_continues_after_prep_error(
        self,
        prep_service,
        mock_calendar_adapter,
        mock_context_gatherer,
    ):
        """scan_and_prepare continues with other meetings after prep error."""
        now = datetime.now(UTC)
        events = [
            {
                "id": "event1",
                "summary": "Meeting 1",
                "start": {"dateTime": (now + timedelta(minutes=10)).isoformat()},
                "end": {"dateTime": (now + timedelta(minutes=70)).isoformat()},
                "attendees": [],
            },
            {
                "id": "event2",
                "summary": "Meeting 2",
                "start": {"dateTime": (now + timedelta(minutes=11)).isoformat()},
                "end": {"dateTime": (now + timedelta(minutes=71)).isoformat()},
                "attendees": [],
            },
        ]
        mock_calendar_adapter.list_upcoming_events.return_value = events

        # First meeting fails, second succeeds
        mock_context_gatherer.gather_for_meeting.side_effect = [
            Exception("Context error"),
            PrepContext(
                open_items=[],
                related_docs=[],
                slack_highlights=[],
                previous_meeting=None,
            ),
        ]

        results = await prep_service.scan_and_prepare()

        # Only second meeting succeeds
        assert len(results) == 1
        assert results[0]["meeting_id"] == "event2"


class TestPrepareForMeeting:
    """Tests for prepare_for_meeting method."""

    def setup_method(self):
        """Reset singleton before each test."""
        PrepService.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        PrepService.reset_instance()

    @pytest.mark.asyncio
    async def test_gathers_context(
        self,
        prep_service,
        mock_context_gatherer,
    ):
        """prepare_for_meeting calls context_gatherer."""
        now = datetime.now(UTC)
        event = {
            "id": "event1",
            "summary": "Test Meeting",
            "start": {"dateTime": now.isoformat()},
            "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
            "attendees": [],
        }

        await prep_service.prepare_for_meeting(
            event=event,
            project_id="proj1",
            project_folder_id="folder1",
            slack_channel_id="C123",
        )

        mock_context_gatherer.gather_for_meeting.assert_called_once()
        call_kwargs = mock_context_gatherer.gather_for_meeting.call_args.kwargs
        assert call_kwargs["project_id"] == "proj1"
        assert call_kwargs["project_folder_id"] == "folder1"
        assert call_kwargs["slack_channel_id"] == "C123"

    @pytest.mark.asyncio
    async def test_sends_to_attendees(
        self,
        prep_service,
        mock_context_gatherer,
        mock_slack_adapter,
    ):
        """prepare_for_meeting sends prep to each attendee with Slack account."""
        now = datetime.now(UTC)
        event = {
            "id": "event1",
            "summary": "Test Meeting",
            "start": {"dateTime": now.isoformat()},
            "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
            "attendees": [
                {"email": "alice@example.com", "displayName": "Alice"},
                {"email": "bob@example.com", "displayName": "Bob"},
            ],
        }

        mock_slack_adapter.lookup_user_by_email.side_effect = [
            {"id": "U123", "name": "alice"},
            {"id": "U456", "name": "bob"},
        ]

        result = await prep_service.prepare_for_meeting(
            event=event,
            project_id="proj1",
        )

        assert result["recipients"] == 2
        assert mock_slack_adapter.send_prep_dm.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_attendees_without_slack(
        self,
        prep_service,
        mock_context_gatherer,
        mock_slack_adapter,
    ):
        """prepare_for_meeting skips attendees not found in Slack."""
        now = datetime.now(UTC)
        event = {
            "id": "event1",
            "summary": "Test Meeting",
            "start": {"dateTime": now.isoformat()},
            "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
            "attendees": [
                {"email": "alice@example.com"},
                {"email": "external@other.com"},
            ],
        }

        # Alice found, external not found
        mock_slack_adapter.lookup_user_by_email.side_effect = [
            {"id": "U123", "name": "alice"},
            None,
        ]

        result = await prep_service.prepare_for_meeting(
            event=event,
            project_id="proj1",
        )

        assert result["recipients"] == 1
        assert mock_slack_adapter.send_prep_dm.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_result_summary(
        self,
        prep_service,
        mock_context_gatherer,
    ):
        """prepare_for_meeting returns summary dict."""
        now = datetime.now(UTC)
        event = {
            "id": "event1",
            "summary": "Test Meeting",
            "start": {"dateTime": now.isoformat()},
            "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
            "attendees": [],
        }

        mock_context_gatherer.gather_for_meeting.return_value = PrepContext(
            open_items=[
                {
                    "id": "item1",
                    "item_type": "action",
                    "description": "Task 1",
                    "owner": "alice@example.com",
                    "due_date": "2026-01-25",
                    "is_overdue": False,
                },
            ],
            related_docs=[],
            slack_highlights=[],
            previous_meeting=None,
        )

        result = await prep_service.prepare_for_meeting(
            event=event,
            project_id="proj1",
        )

        assert result["meeting_id"] == "event1"
        assert result["meeting_title"] == "Test Meeting"
        assert result["items"] == 1
        assert result["talking_points"] >= 1  # At least one talking point

    @pytest.mark.asyncio
    async def test_handles_malformed_event_dates(
        self,
        prep_service,
        mock_context_gatherer,
    ):
        """prepare_for_meeting handles events with missing/malformed dates."""
        event = {
            "id": "event1",
            "summary": "Test Meeting",
            "start": {},  # Missing dateTime
            "end": {},
            "attendees": [],
        }

        # Should not raise, uses fallback dates
        result = await prep_service.prepare_for_meeting(
            event=event,
            project_id="proj1",
        )

        assert result["meeting_id"] == "event1"

    @pytest.mark.asyncio
    async def test_includes_previous_meeting_url(
        self,
        prep_service,
        mock_context_gatherer,
        mock_slack_adapter,
    ):
        """prepare_for_meeting includes previous meeting URL in blocks."""
        now = datetime.now(UTC)
        event = {
            "id": "event1",
            "summary": "Weekly Sync",
            "start": {"dateTime": now.isoformat()},
            "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
            "attendees": [{"email": "alice@example.com"}],
        }

        mock_context_gatherer.gather_for_meeting.return_value = PrepContext(
            open_items=[],
            related_docs=[],
            slack_highlights=[],
            previous_meeting={
                "url": "https://docs.google.com/doc/123",
                "date": "2026-01-12",
            },
        )

        mock_slack_adapter.lookup_user_by_email.return_value = {"id": "U123"}

        await prep_service.prepare_for_meeting(event=event, project_id="proj1")

        # Check that blocks include the URL
        call_kwargs = mock_slack_adapter.send_prep_dm.call_args.kwargs
        blocks = call_kwargs["blocks"]

        # Find context block with links
        links_found = False
        for block in blocks:
            if block.get("type") == "context":
                for element in block.get("elements", []):
                    if "https://docs.google.com/doc/123" in element.get("text", ""):
                        links_found = True
                        break

        assert links_found

    @pytest.mark.asyncio
    async def test_uses_config_settings(
        self,
        mock_calendar_adapter,
        mock_slack_adapter,
        mock_item_matcher,
        mock_context_gatherer,
    ):
        """prepare_for_meeting uses config for lookback_days and max_items."""
        config = PrepConfig(
            lead_time_minutes=15,
            max_items=5,
            lookback_days=30,
        )

        service = PrepService(
            calendar_adapter=mock_calendar_adapter,
            slack_adapter=mock_slack_adapter,
            item_matcher=mock_item_matcher,
            context_gatherer=mock_context_gatherer,
            config=config,
        )

        now = datetime.now(UTC)
        event = {
            "id": "event1",
            "summary": "Test",
            "start": {"dateTime": now.isoformat()},
            "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
            "attendees": [],
        }

        await service.prepare_for_meeting(event=event, project_id="proj1")

        call_kwargs = mock_context_gatherer.gather_for_meeting.call_args.kwargs
        assert call_kwargs["lookback_days"] == 30

    @pytest.mark.asyncio
    async def test_handles_send_failure(
        self,
        prep_service,
        mock_context_gatherer,
        mock_slack_adapter,
    ):
        """prepare_for_meeting handles DM send failures gracefully."""
        now = datetime.now(UTC)
        event = {
            "id": "event1",
            "summary": "Test",
            "start": {"dateTime": now.isoformat()},
            "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
            "attendees": [{"email": "alice@example.com"}],
        }

        mock_slack_adapter.lookup_user_by_email.return_value = {"id": "U123"}
        mock_slack_adapter.send_prep_dm.return_value = {
            "success": False,
            "error": "channel_not_found",
        }

        result = await prep_service.prepare_for_meeting(event=event, project_id="proj1")

        # Should report 0 recipients despite attempt
        assert result["recipients"] == 0


class TestDefaultConfig:
    """Tests for default configuration."""

    def setup_method(self):
        """Reset singleton before each test."""
        PrepService.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        PrepService.reset_instance()

    def test_default_config_values(
        self,
        mock_calendar_adapter,
        mock_slack_adapter,
        mock_item_matcher,
        mock_context_gatherer,
    ):
        """PrepService uses default config when not provided."""
        service = PrepService(
            calendar_adapter=mock_calendar_adapter,
            slack_adapter=mock_slack_adapter,
            item_matcher=mock_item_matcher,
            context_gatherer=mock_context_gatherer,
        )

        assert service._config.lead_time_minutes == 10
        assert service._config.max_items == 10
        assert service._config.lookback_days == 90
