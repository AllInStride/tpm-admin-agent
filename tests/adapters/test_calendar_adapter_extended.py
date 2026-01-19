"""Tests for CalendarAdapter list_upcoming_events extension."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.calendar_adapter import CalendarAdapter


@pytest.fixture
def calendar_adapter():
    """Create CalendarAdapter with mock credentials path."""
    with patch.dict("os.environ", {"GOOGLE_CALENDAR_CREDENTIALS": "/fake/path.json"}):
        adapter = CalendarAdapter()
        # Pre-set a mock service to avoid actual credential loading
        adapter._service = MagicMock()
        yield adapter


class TestListUpcomingEvents:
    """Tests for CalendarAdapter.list_upcoming_events."""

    @pytest.mark.asyncio
    async def test_returns_events_in_time_window(self, calendar_adapter):
        """list_upcoming_events returns events within time window."""
        mock_events = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Team Sync",
                    "start": {"dateTime": "2026-01-20T10:00:00Z"},
                    "end": {"dateTime": "2026-01-20T11:00:00Z"},
                    "attendees": [
                        {"email": "alice@example.com", "displayName": "Alice"},
                        {"email": "bob@example.com", "responseStatus": "accepted"},
                    ],
                },
                {
                    "id": "event2",
                    "summary": "Project Review",
                    "start": {"dateTime": "2026-01-20T14:00:00Z"},
                    "end": {"dateTime": "2026-01-20T15:00:00Z"},
                    "attendees": [],
                },
            ]
        }

        calendar_adapter._service.events().list().execute.return_value = mock_events

        time_min = datetime(2026, 1, 20, 9, 0, tzinfo=UTC)
        time_max = datetime(2026, 1, 20, 16, 0, tzinfo=UTC)

        events = await calendar_adapter.list_upcoming_events(
            calendar_id="user@example.com",
            time_min=time_min,
            time_max=time_max,
        )

        assert len(events) == 2
        assert events[0]["id"] == "event1"
        assert events[0]["summary"] == "Team Sync"
        assert len(events[0]["attendees"]) == 2
        assert events[1]["id"] == "event2"
        assert events[1]["summary"] == "Project Review"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_events(self, calendar_adapter):
        """list_upcoming_events returns empty list when no events found."""
        calendar_adapter._service.events().list().execute.return_value = {"items": []}

        time_min = datetime(2026, 1, 20, 9, 0, tzinfo=UTC)
        time_max = datetime(2026, 1, 20, 16, 0, tzinfo=UTC)

        events = await calendar_adapter.list_upcoming_events(
            calendar_id="user@example.com",
            time_min=time_min,
            time_max=time_max,
        )

        assert events == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_error(self, calendar_adapter):
        """list_upcoming_events returns empty list on API error."""
        calendar_adapter._service.events().list().execute.side_effect = Exception(
            "API Error"
        )

        time_min = datetime(2026, 1, 20, 9, 0, tzinfo=UTC)
        time_max = datetime(2026, 1, 20, 16, 0, tzinfo=UTC)

        events = await calendar_adapter.list_upcoming_events(
            calendar_id="user@example.com",
            time_min=time_min,
            time_max=time_max,
        )

        assert events == []

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_params(self, calendar_adapter):
        """list_upcoming_events calls API with correct parameters."""
        calendar_adapter._service.events().list().execute.return_value = {"items": []}

        time_min = datetime(2026, 1, 20, 9, 0, tzinfo=UTC)
        time_max = datetime(2026, 1, 20, 16, 0, tzinfo=UTC)

        await calendar_adapter.list_upcoming_events(
            calendar_id="user@example.com",
            time_min=time_min,
            time_max=time_max,
            max_results=25,
        )

        calendar_adapter._service.events().list.assert_called_with(
            calendarId="user@example.com",
            timeMin="2026-01-20T09:00:00+00:00",
            timeMax="2026-01-20T16:00:00+00:00",
            maxResults=25,
            singleEvents=True,
            orderBy="startTime",
        )

    @pytest.mark.asyncio
    async def test_handles_events_without_attendees(self, calendar_adapter):
        """list_upcoming_events handles events with no attendees field."""
        mock_events = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Solo Work",
                    "start": {"dateTime": "2026-01-20T10:00:00Z"},
                    "end": {"dateTime": "2026-01-20T11:00:00Z"},
                    # No attendees field
                },
            ]
        }

        calendar_adapter._service.events().list().execute.return_value = mock_events

        time_min = datetime(2026, 1, 20, 9, 0)
        time_max = datetime(2026, 1, 20, 16, 0)

        events = await calendar_adapter.list_upcoming_events(
            calendar_id="user@example.com",
            time_min=time_min,
            time_max=time_max,
        )

        assert len(events) == 1
        assert events[0]["attendees"] == []

    @pytest.mark.asyncio
    async def test_handles_events_without_summary(self, calendar_adapter):
        """list_upcoming_events handles events with no summary."""
        mock_events = {
            "items": [
                {
                    "id": "event1",
                    # No summary field
                    "start": {"dateTime": "2026-01-20T10:00:00Z"},
                    "end": {"dateTime": "2026-01-20T11:00:00Z"},
                },
            ]
        }

        calendar_adapter._service.events().list().execute.return_value = mock_events

        time_min = datetime(2026, 1, 20, 9, 0)
        time_max = datetime(2026, 1, 20, 16, 0)

        events = await calendar_adapter.list_upcoming_events(
            calendar_id="user@example.com",
            time_min=time_min,
            time_max=time_max,
        )

        assert len(events) == 1
        assert events[0]["summary"] == ""

    @pytest.mark.asyncio
    async def test_default_max_results(self, calendar_adapter):
        """list_upcoming_events uses default max_results of 50."""
        calendar_adapter._service.events().list().execute.return_value = {"items": []}

        time_min = datetime(2026, 1, 20, 9, 0)
        time_max = datetime(2026, 1, 20, 16, 0)

        await calendar_adapter.list_upcoming_events(
            calendar_id="user@example.com",
            time_min=time_min,
            time_max=time_max,
        )

        call_kwargs = calendar_adapter._service.events().list.call_args.kwargs
        assert call_kwargs["maxResults"] == 50

    @pytest.mark.asyncio
    async def test_handles_naive_datetime(self, calendar_adapter):
        """list_upcoming_events handles naive datetime by appending Z."""
        calendar_adapter._service.events().list().execute.return_value = {"items": []}

        # Naive datetime (no timezone)
        time_min = datetime(2026, 1, 20, 9, 0)
        time_max = datetime(2026, 1, 20, 16, 0)

        await calendar_adapter.list_upcoming_events(
            calendar_id="user@example.com",
            time_min=time_min,
            time_max=time_max,
        )

        call_kwargs = calendar_adapter._service.events().list.call_args.kwargs
        assert call_kwargs["timeMin"] == "2026-01-20T09:00:00Z"
        assert call_kwargs["timeMax"] == "2026-01-20T16:00:00Z"
