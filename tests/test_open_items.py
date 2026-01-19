"""Tests for open item definition and schemas."""

from datetime import datetime

import pytest

from src.search.open_items import (
    CLOSED_STATUSES,
    GroupedOpenItems,
    ItemHistory,
    ItemHistoryEntry,
    OpenItemFilter,
    OpenItemSummary,
    classify_change,
    is_item_open,
)


class TestIsItemOpen:
    """Tests for is_item_open function."""

    def test_pending_is_open(self):
        """Pending items are open."""
        assert is_item_open("pending") is True

    def test_completed_is_closed(self):
        """Completed items are closed."""
        assert is_item_open("completed") is False

    def test_cancelled_is_closed(self):
        """Cancelled items are closed."""
        assert is_item_open("cancelled") is False

    def test_closed_is_closed(self):
        """Closed items are closed."""
        assert is_item_open("closed") is False

    def test_resolved_is_closed(self):
        """Resolved items are closed."""
        assert is_item_open("resolved") is False

    def test_none_status_is_open(self):
        """None status defaults to open."""
        assert is_item_open(None) is True

    def test_case_insensitive_completed(self):
        """Case insensitivity for COMPLETED."""
        assert is_item_open("COMPLETED") is False

    def test_case_insensitive_cancelled(self):
        """Case insensitivity for Cancelled."""
        assert is_item_open("Cancelled") is False

    def test_in_progress_is_open(self):
        """In progress items are open."""
        assert is_item_open("in_progress") is True

    def test_blocked_is_open(self):
        """Blocked items are open."""
        assert is_item_open("blocked") is True


class TestClosedStatuses:
    """Tests for CLOSED_STATUSES constant."""

    def test_closed_statuses_is_frozenset(self):
        """CLOSED_STATUSES should be immutable."""
        assert isinstance(CLOSED_STATUSES, frozenset)

    def test_closed_statuses_contains_expected(self):
        """CLOSED_STATUSES has all expected values."""
        expected = {"completed", "cancelled", "closed", "resolved"}
        assert CLOSED_STATUSES == expected


class TestClassifyChange:
    """Tests for classify_change function."""

    def test_extracted_events_are_created(self):
        """Events with 'Extracted' are classified as created."""
        assert classify_change("ActionItemExtracted") == "created"
        assert classify_change("DecisionExtracted") == "created"
        assert classify_change("RiskExtracted") == "created"
        assert classify_change("IssueExtracted") == "created"

    def test_updated_events_are_updated(self):
        """Events with 'Updated' are classified as updated."""
        assert classify_change("ActionItemUpdated") == "updated"
        assert classify_change("StatusUpdated") == "updated"

    def test_other_events_are_mentioned(self):
        """Other events are classified as mentioned."""
        assert classify_change("MeetingCreated") == "mentioned"
        assert classify_change("TranscriptParsed") == "mentioned"
        assert classify_change("ItemReferenced") == "mentioned"


class TestOpenItemFilter:
    """Tests for OpenItemFilter schema."""

    def test_default_values(self):
        """Filter has sensible defaults."""
        filter = OpenItemFilter()
        assert filter.item_type is None
        assert filter.owner is None
        assert filter.meeting_id is None
        assert filter.overdue_only is False
        assert filter.due_within_days is None

    def test_filter_with_item_type(self):
        """Filter accepts item_type."""
        filter = OpenItemFilter(item_type="action")
        assert filter.item_type == "action"

    def test_filter_with_owner(self):
        """Filter accepts owner."""
        filter = OpenItemFilter(owner="John Smith")
        assert filter.owner == "John Smith"

    def test_filter_with_due_within_days(self):
        """Filter accepts due_within_days."""
        filter = OpenItemFilter(due_within_days=7)
        assert filter.due_within_days == 7

    def test_filter_due_within_days_validates_non_negative(self):
        """due_within_days must be non-negative."""
        with pytest.raises(ValueError):
            OpenItemFilter(due_within_days=-1)

    def test_filter_serialization(self):
        """Filter can be serialized to dict."""
        filter = OpenItemFilter(item_type="risk", overdue_only=True)
        data = filter.model_dump()
        assert data["item_type"] == "risk"
        assert data["overdue_only"] is True


class TestOpenItemSummary:
    """Tests for OpenItemSummary schema."""

    def test_summary_creation(self):
        """Summary can be created with counts."""
        summary = OpenItemSummary(
            total=10,
            overdue=3,
            due_today=2,
            due_this_week=5,
            by_type={"action": 6, "risk": 4},
        )
        assert summary.total == 10
        assert summary.overdue == 3
        assert summary.due_today == 2
        assert summary.due_this_week == 5
        assert summary.by_type == {"action": 6, "risk": 4}

    def test_summary_default_by_type(self):
        """by_type defaults to empty dict."""
        summary = OpenItemSummary(total=0, overdue=0, due_today=0, due_this_week=0)
        assert summary.by_type == {}

    def test_summary_serialization(self):
        """Summary can be serialized."""
        summary = OpenItemSummary(
            total=5,
            overdue=1,
            due_today=0,
            due_this_week=4,
            by_type={"action": 5},
        )
        data = summary.model_dump()
        assert data["total"] == 5
        assert data["by_type"]["action"] == 5


class TestGroupedOpenItems:
    """Tests for GroupedOpenItems schema."""

    def test_grouped_items_creation(self):
        """GroupedOpenItems can be created."""
        summary = OpenItemSummary(total=2, overdue=0, due_today=1, due_this_week=1)
        items = [
            {"id": "1", "description": "Test"},
            {"id": "2", "description": "Test 2"},
        ]
        grouped = GroupedOpenItems(summary=summary, items=items, group_by="owner")
        assert grouped.summary.total == 2
        assert len(grouped.items) == 2
        assert grouped.group_by == "owner"

    def test_grouped_items_default_group_by(self):
        """group_by defaults to due_date."""
        summary = OpenItemSummary(total=0, overdue=0, due_today=0, due_this_week=0)
        grouped = GroupedOpenItems(summary=summary)
        assert grouped.group_by == "due_date"


class TestItemHistoryEntry:
    """Tests for ItemHistoryEntry schema."""

    def test_history_entry_creation(self):
        """ItemHistoryEntry can be created."""
        entry = ItemHistoryEntry(
            timestamp=datetime(2026, 1, 15, 10, 0, 0),
            event_type="ActionItemExtracted",
            change_type="created",
            meeting_id="meeting-123",
            meeting_title="Sprint Planning",
            meeting_date="2026-01-15",
        )
        assert entry.event_type == "ActionItemExtracted"
        assert entry.change_type == "created"
        assert entry.meeting_title == "Sprint Planning"

    def test_history_entry_optional_fields(self):
        """Meeting fields are optional."""
        entry = ItemHistoryEntry(
            timestamp=datetime(2026, 1, 15, 10, 0, 0),
            event_type="StatusUpdated",
            change_type="updated",
        )
        assert entry.meeting_id is None
        assert entry.meeting_title is None
        assert entry.meeting_date is None


class TestItemHistory:
    """Tests for ItemHistory schema."""

    def test_item_history_creation(self):
        """ItemHistory can be created."""
        entry1 = ItemHistoryEntry(
            timestamp=datetime(2026, 1, 15, 10, 0, 0),
            event_type="ActionItemExtracted",
            change_type="created",
        )
        entry2 = ItemHistoryEntry(
            timestamp=datetime(2026, 1, 16, 14, 0, 0),
            event_type="ActionItemUpdated",
            change_type="updated",
        )
        history = ItemHistory(
            item_id="action-123",
            item_type="action",
            description="Complete API documentation",
            current_status="pending",
            entries=[entry1, entry2],
        )
        assert history.item_id == "action-123"
        assert history.item_type == "action"
        assert len(history.entries) == 2
        assert history.entries[0].change_type == "created"

    def test_item_history_default_entries(self):
        """entries defaults to empty list."""
        history = ItemHistory(
            item_id="item-1",
            item_type="decision",
            description="Test decision",
            current_status="pending",
        )
        assert history.entries == []
