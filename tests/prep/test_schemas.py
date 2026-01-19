"""Tests for prep schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.prep.schemas import (
    CalendarEvent,
    MeetingPrepRequest,
    PrepConfig,
    PrepItem,
    PrepSummary,
    TalkingPoint,
)


class TestPrepConfig:
    """Tests for PrepConfig model."""

    def test_default_values(self):
        """PrepConfig has sensible defaults."""
        config = PrepConfig()
        assert config.lead_time_minutes == 10
        assert config.delivery_method == "slack"
        assert config.max_items == 10
        assert config.lookback_days == 90

    def test_custom_values(self):
        """PrepConfig accepts custom values."""
        config = PrepConfig(
            lead_time_minutes=15,
            delivery_method="email",
            max_items=5,
            lookback_days=30,
        )
        assert config.lead_time_minutes == 15
        assert config.delivery_method == "email"
        assert config.max_items == 5
        assert config.lookback_days == 30

    def test_invalid_delivery_method(self):
        """PrepConfig rejects invalid delivery method."""
        with pytest.raises(ValidationError):
            PrepConfig(delivery_method="sms")

    def test_lead_time_bounds(self):
        """PrepConfig validates lead_time_minutes bounds."""
        # Valid bounds
        PrepConfig(lead_time_minutes=1)
        PrepConfig(lead_time_minutes=60)

        # Invalid: too low
        with pytest.raises(ValidationError):
            PrepConfig(lead_time_minutes=0)

        # Invalid: too high
        with pytest.raises(ValidationError):
            PrepConfig(lead_time_minutes=61)

    def test_max_items_bounds(self):
        """PrepConfig validates max_items bounds."""
        PrepConfig(max_items=1)
        PrepConfig(max_items=50)

        with pytest.raises(ValidationError):
            PrepConfig(max_items=0)

        with pytest.raises(ValidationError):
            PrepConfig(max_items=51)

    def test_lookback_days_bounds(self):
        """PrepConfig validates lookback_days bounds."""
        PrepConfig(lookback_days=1)
        PrepConfig(lookback_days=365)

        with pytest.raises(ValidationError):
            PrepConfig(lookback_days=0)

        with pytest.raises(ValidationError):
            PrepConfig(lookback_days=366)


class TestCalendarEvent:
    """Tests for CalendarEvent model."""

    def test_valid_event(self):
        """CalendarEvent accepts valid data."""
        event = CalendarEvent(
            id="event123",
            summary="Team Sync",
            start=datetime(2026, 1, 20, 10, 0, tzinfo=UTC),
            end=datetime(2026, 1, 20, 11, 0, tzinfo=UTC),
            attendees=[
                {"email": "alice@example.com", "displayName": "Alice"},
                {"email": "bob@example.com", "responseStatus": "accepted"},
            ],
        )
        assert event.id == "event123"
        assert event.summary == "Team Sync"
        assert len(event.attendees) == 2

    def test_empty_attendees_default(self):
        """CalendarEvent defaults to empty attendees list."""
        event = CalendarEvent(
            id="event123",
            summary="Solo Meeting",
            start=datetime(2026, 1, 20, 10, 0),
            end=datetime(2026, 1, 20, 11, 0),
        )
        assert event.attendees == []

    def test_required_fields(self):
        """CalendarEvent requires id, summary, start, end."""
        with pytest.raises(ValidationError):
            CalendarEvent(id="event123")


class TestPrepItem:
    """Tests for PrepItem model."""

    def test_valid_prep_item(self):
        """PrepItem accepts valid data."""
        item = PrepItem(
            id="item123",
            item_type="action",
            description="Complete the design doc",
            owner="alice@example.com",
            due_date="2026-01-25",
            is_overdue=True,
            is_new=False,
        )
        assert item.id == "item123"
        assert item.item_type == "action"
        assert item.is_overdue is True

    def test_optional_fields(self):
        """PrepItem has optional owner and due_date."""
        item = PrepItem(
            id="item123",
            item_type="risk",
            description="Resource availability",
        )
        assert item.owner is None
        assert item.due_date is None
        assert item.is_overdue is False
        assert item.is_new is False

    def test_required_fields(self):
        """PrepItem requires id, item_type, description."""
        with pytest.raises(ValidationError):
            PrepItem(id="item123")


class TestTalkingPoint:
    """Tests for TalkingPoint model."""

    def test_valid_talking_point(self):
        """TalkingPoint accepts valid data."""
        point = TalkingPoint(
            text="Review 3 overdue items",
            category="overdue",
        )
        assert point.text == "Review 3 overdue items"
        assert point.category == "overdue"

    def test_valid_categories(self):
        """TalkingPoint accepts all valid categories."""
        for category in ["overdue", "risk", "new_item", "general"]:
            point = TalkingPoint(text="Test point", category=category)
            assert point.category == category

    def test_invalid_category(self):
        """TalkingPoint rejects invalid categories."""
        with pytest.raises(ValidationError):
            TalkingPoint(text="Test", category="invalid")


class TestPrepSummary:
    """Tests for PrepSummary model."""

    def test_valid_prep_summary(self):
        """PrepSummary accepts valid data."""
        event = CalendarEvent(
            id="event123",
            summary="Team Sync",
            start=datetime(2026, 1, 20, 10, 0, tzinfo=UTC),
            end=datetime(2026, 1, 20, 11, 0, tzinfo=UTC),
        )
        item = PrepItem(
            id="item1",
            item_type="action",
            description="Complete task",
        )
        point = TalkingPoint(text="Discuss progress", category="general")

        summary = PrepSummary(
            meeting=event,
            open_items=[item],
            talking_points=[point],
            recent_meeting_url="https://docs.google.com/doc/123",
            full_prep_url="https://app.example.com/prep/456",
            attendees=[{"name": "Alice", "role": "PM"}],
        )

        assert summary.meeting.id == "event123"
        assert len(summary.open_items) == 1
        assert len(summary.talking_points) == 1
        assert summary.attendees[0]["name"] == "Alice"

    def test_default_values(self):
        """PrepSummary has sensible defaults."""
        event = CalendarEvent(
            id="event123",
            summary="Meeting",
            start=datetime(2026, 1, 20, 10, 0),
            end=datetime(2026, 1, 20, 11, 0),
        )
        summary = PrepSummary(meeting=event)

        assert summary.open_items == []
        assert summary.talking_points == []
        assert summary.recent_meeting_url is None
        assert summary.full_prep_url is None
        assert summary.attendees == []


class TestMeetingPrepRequest:
    """Tests for MeetingPrepRequest model."""

    def test_valid_request(self):
        """MeetingPrepRequest accepts valid data."""
        request = MeetingPrepRequest(
            calendar_id="user@example.com",
            event_id="event123",
            project_id="proj456",
        )
        assert request.calendar_id == "user@example.com"
        assert request.event_id == "event123"
        assert request.project_id == "proj456"

    def test_required_fields(self):
        """MeetingPrepRequest requires all fields."""
        with pytest.raises(ValidationError):
            MeetingPrepRequest(calendar_id="user@example.com")

        with pytest.raises(ValidationError):
            MeetingPrepRequest(
                calendar_id="user@example.com",
                event_id="event123",
            )
