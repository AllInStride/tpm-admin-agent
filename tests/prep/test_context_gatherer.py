"""Tests for ContextGatherer and normalize_series_key."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.prep.context_gatherer import ContextGatherer, PrepContext, normalize_series_key
from src.prep.schemas import CalendarEvent


class TestNormalizeSeriesKey:
    """Tests for normalize_series_key function."""

    def test_strips_slash_dates(self):
        """Should strip MM/DD dates from title."""
        result = normalize_series_key("Project Alpha SteerCo 01/15")
        assert result == "project alpha steerco"

    def test_strips_iso_dates(self):
        """Should strip YYYY-MM-DD dates from title."""
        result = normalize_series_key("DSU 2026-01-19")
        assert result == "dsu"

    def test_strips_standalone_numbers(self):
        """Should strip standalone numbers (week numbers, etc)."""
        result = normalize_series_key("Weekly Sync - Week 3")
        assert result == "weekly sync - week"

    def test_preserves_numbers_in_words(self):
        """Should preserve numbers that are part of words."""
        result = normalize_series_key("Phase2 Review")
        assert result == "phase2 review"

    def test_lowercases_result(self):
        """Should lowercase the result."""
        result = normalize_series_key("Project ALPHA SteerCo")
        assert result == "project alpha steerco"

    def test_empty_string(self):
        """Should return empty string for empty input."""
        assert normalize_series_key("") == ""


class TestContextGatherer:
    """Tests for ContextGatherer class."""

    @pytest.fixture
    def mock_meeting(self):
        """Create a mock CalendarEvent."""
        return CalendarEvent(
            id="event123",
            summary="Project Alpha Weekly Sync",
            start=datetime(2026, 1, 19, 10, 0),
            end=datetime(2026, 1, 19, 11, 0),
            attendees=[
                {"email": "alice@example.com", "displayName": "Alice"},
                {"email": "bob@example.com", "displayName": "Bob"},
            ],
        )

    @pytest.fixture
    def mock_item_matcher(self):
        """Create a mock ItemMatcher."""
        matcher = MagicMock()
        matcher.get_items_for_prep = AsyncMock(
            return_value=[
                {
                    "id": "item1",
                    "description": "Complete API spec",
                    "owner": "alice@example.com",
                    "item_type": "action",
                    "is_overdue": False,
                }
            ]
        )
        return matcher

    @pytest.fixture
    def mock_drive_adapter(self):
        """Create a mock DriveAdapter."""
        adapter = MagicMock()
        adapter.search_project_docs = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "name": "Project Spec.docx",
                    "webViewLink": "https://drive.google.com/file/d/doc1/view",
                }
            ]
        )
        return adapter

    @pytest.fixture
    def mock_slack_adapter(self):
        """Create a mock SlackAdapter."""
        adapter = MagicMock()
        adapter.get_channel_history = AsyncMock(
            return_value=[
                {"text": "Latest update", "user": "U123", "ts": "1234567890.123"}
            ]
        )
        return adapter

    @pytest.mark.asyncio
    async def test_parallel_gathering_all_sources(
        self,
        mock_meeting,
        mock_item_matcher,
        mock_drive_adapter,
        mock_slack_adapter,
    ):
        """Should gather from all sources in parallel."""
        gatherer = ContextGatherer(
            item_matcher=mock_item_matcher,
            drive_adapter=mock_drive_adapter,
            slack_adapter=mock_slack_adapter,
        )

        result = await gatherer.gather_for_meeting(
            meeting=mock_meeting,
            project_id="proj123",
            project_folder_id="folder123",
            slack_channel_id="C123",
        )

        assert isinstance(result, PrepContext)
        assert len(result.open_items) == 1
        assert len(result.related_docs) == 1
        assert len(result.slack_highlights) == 1

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_item_matcher(
        self, mock_meeting, mock_drive_adapter
    ):
        """Should work without ItemMatcher (returns empty items)."""
        gatherer = ContextGatherer(
            item_matcher=None,
            drive_adapter=mock_drive_adapter,
        )

        result = await gatherer.gather_for_meeting(
            meeting=mock_meeting,
            project_id="proj123",
            project_folder_id="folder123",
        )

        assert result.open_items == []
        assert len(result.related_docs) == 1

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_drive(self, mock_meeting, mock_item_matcher):
        """Should work without DriveAdapter (returns empty docs)."""
        gatherer = ContextGatherer(
            item_matcher=mock_item_matcher,
            drive_adapter=None,
        )

        result = await gatherer.gather_for_meeting(
            meeting=mock_meeting,
            project_id="proj123",
            project_folder_id="folder123",
        )

        assert len(result.open_items) == 1
        assert result.related_docs == []

    @pytest.mark.asyncio
    async def test_individual_source_failure_doesnt_block_others(
        self,
        mock_meeting,
        mock_item_matcher,
        mock_drive_adapter,
        mock_slack_adapter,
    ):
        """Should continue gathering if one source fails."""
        mock_item_matcher.get_items_for_prep = AsyncMock(
            side_effect=Exception("Database error")
        )

        gatherer = ContextGatherer(
            item_matcher=mock_item_matcher,
            drive_adapter=mock_drive_adapter,
            slack_adapter=mock_slack_adapter,
        )

        result = await gatherer.gather_for_meeting(
            meeting=mock_meeting,
            project_id="proj123",
            project_folder_id="folder123",
            slack_channel_id="C123",
        )

        assert result.open_items == []
        assert len(result.related_docs) == 1
        assert len(result.slack_highlights) == 1

    @pytest.mark.asyncio
    async def test_all_adapters_none(self, mock_meeting):
        """Should return empty PrepContext when all adapters are None."""
        gatherer = ContextGatherer()

        result = await gatherer.gather_for_meeting(
            meeting=mock_meeting,
            project_id="proj123",
        )

        assert result.open_items == []
        assert result.related_docs == []
        assert result.slack_highlights == []
        assert result.previous_meeting is None
