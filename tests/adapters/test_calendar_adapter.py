"""Tests for CalendarAdapter."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.calendar_adapter import CalendarAdapter


@pytest.fixture
def mock_build():
    """Mock googleapiclient.discovery.build."""
    with patch("src.adapters.calendar_adapter.build") as mock:
        yield mock


@pytest.fixture
def mock_credentials():
    """Mock google.oauth2.service_account.Credentials."""
    with patch("src.adapters.calendar_adapter.Credentials") as mock:
        yield mock


class TestCalendarAdapterInit:
    """Tests for CalendarAdapter initialization."""

    def test_uses_provided_credentials(self, mock_build, mock_credentials):
        """Should use credentials path passed to constructor."""
        adapter = CalendarAdapter(credentials_path="/path/to/creds.json")
        adapter._get_service()

        mock_credentials.from_service_account_file.assert_called_once()
        call_args = mock_credentials.from_service_account_file.call_args
        assert call_args[0][0] == "/path/to/creds.json"

    def test_falls_back_to_calendar_env_var(
        self, mock_build, mock_credentials, monkeypatch
    ):
        """Should fall back to GOOGLE_CALENDAR_CREDENTIALS env var."""
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", "/env/creds.json")
        adapter = CalendarAdapter()
        adapter._get_service()

        call_args = mock_credentials.from_service_account_file.call_args
        assert call_args[0][0] == "/env/creds.json"

    def test_falls_back_to_sheets_env_var(
        self, mock_build, mock_credentials, monkeypatch
    ):
        """Should fall back to GOOGLE_SHEETS_CREDENTIALS if calendar not set."""
        monkeypatch.delenv("GOOGLE_CALENDAR_CREDENTIALS", raising=False)
        monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", "/sheets/creds.json")
        adapter = CalendarAdapter()
        adapter._get_service()

        call_args = mock_credentials.from_service_account_file.call_args
        assert call_args[0][0] == "/sheets/creds.json"

    def test_no_credentials_raises_value_error(self, mock_build, monkeypatch):
        """Should raise ValueError when no credentials available."""
        monkeypatch.delenv("GOOGLE_CALENDAR_CREDENTIALS", raising=False)
        monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
        adapter = CalendarAdapter()

        with pytest.raises(ValueError, match="No credentials"):
            adapter._get_service()


class TestGetEventAttendees:
    """Tests for get_event_attendees method."""

    @pytest.mark.asyncio
    async def test_returns_attendee_list(self, mock_build, mock_credentials):
        """Should return list of attendees from event."""
        mock_service = MagicMock()
        mock_service.events().get().execute.return_value = {
            "attendees": [
                {"email": "alice@example.com", "displayName": "Alice"},
                {"email": "bob@example.com", "displayName": "Bob"},
            ]
        }
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        result = await adapter.get_event_attendees("cal@example.com", "event123")

        assert len(result) == 2
        assert result[0]["email"] == "alice@example.com"
        assert result[1]["email"] == "bob@example.com"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_attendees(
        self, mock_build, mock_credentials
    ):
        """Should return empty list when event has no attendees."""
        mock_service = MagicMock()
        mock_service.events().get().execute.return_value = {}
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        result = await adapter.get_event_attendees("cal@example.com", "event123")

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self, mock_build, mock_credentials):
        """Should return empty list on API error."""
        mock_service = MagicMock()
        mock_service.events().get().execute.side_effect = RuntimeError("API Error")
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        result = await adapter.get_event_attendees("cal@example.com", "event123")

        assert result == []


class TestVerifyAttendee:
    """Tests for verify_attendee method."""

    @pytest.mark.asyncio
    async def test_returns_true_when_present(self, mock_build, mock_credentials):
        """Should return True when email is in attendees."""
        mock_service = MagicMock()
        mock_service.events().get().execute.return_value = {
            "attendees": [
                {"email": "alice@example.com"},
                {"email": "bob@example.com"},
            ]
        }
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        result = await adapter.verify_attendee(
            "cal@example.com", "event123", "alice@example.com"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_absent(self, mock_build, mock_credentials):
        """Should return False when email not in attendees."""
        mock_service = MagicMock()
        mock_service.events().get().execute.return_value = {
            "attendees": [
                {"email": "alice@example.com"},
                {"email": "bob@example.com"},
            ]
        }
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        result = await adapter.verify_attendee(
            "cal@example.com", "event123", "charlie@example.com"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_case_insensitive_email_matching(self, mock_build, mock_credentials):
        """Should match emails case-insensitively."""
        mock_service = MagicMock()
        mock_service.events().get().execute.return_value = {
            "attendees": [{"email": "Alice@Example.COM"}]
        }
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        result = await adapter.verify_attendee(
            "cal@example.com", "event123", "alice@example.com"
        )

        assert result is True


class TestFindMeetingByTime:
    """Tests for find_meeting_by_time method."""

    @pytest.mark.asyncio
    async def test_returns_event_id_when_found(self, mock_build, mock_credentials):
        """Should return event ID when meeting found."""
        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {
            "items": [
                {"id": "event123", "summary": "Team Meeting"},
            ]
        }
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        meeting_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        result = await adapter.find_meeting_by_time("cal@example.com", meeting_time)

        assert result == "event123"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_build, mock_credentials):
        """Should return None when no meeting found."""
        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {"items": []}
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        meeting_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        result = await adapter.find_meeting_by_time("cal@example.com", meeting_time)

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self, mock_build, mock_credentials):
        """Should return None on API error."""
        mock_service = MagicMock()
        mock_service.events().list().execute.side_effect = RuntimeError("API Error")
        mock_build.return_value = mock_service

        adapter = CalendarAdapter(credentials_path="/test/creds.json")
        meeting_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        result = await adapter.find_meeting_by_time("cal@example.com", meeting_time)

        assert result is None
