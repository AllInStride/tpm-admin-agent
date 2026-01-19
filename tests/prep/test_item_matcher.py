"""Tests for ItemMatcher and item prioritization."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.turso import TursoClient
from src.prep.item_matcher import (
    ItemMatcher,
    generate_talking_points,
    prioritize_items,
)
from src.prep.schemas import TalkingPoint


class TestPrioritizeItems:
    """Tests for prioritize_items function."""

    def test_overdue_items_first(self):
        """Overdue items should be sorted before non-overdue items."""
        items = [
            {
                "id": "1",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-25",
            },
            {
                "id": "2",
                "is_overdue": True,
                "item_type": "action",
                "due_date": "2026-01-15",
            },
            {
                "id": "3",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-20",
            },
        ]

        result = prioritize_items(items)

        assert result[0]["id"] == "2"  # Overdue first
        assert result[1]["id"] == "3"  # Then by due date
        assert result[2]["id"] == "1"

    def test_type_order_after_overdue(self):
        """Items sorted by type: action > risk > issue > decision."""
        items = [
            {
                "id": "1",
                "is_overdue": False,
                "item_type": "decision",
                "due_date": "2026-01-20",
            },
            {
                "id": "2",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-20",
            },
            {
                "id": "3",
                "is_overdue": False,
                "item_type": "issue",
                "due_date": "2026-01-20",
            },
            {
                "id": "4",
                "is_overdue": False,
                "item_type": "risk",
                "due_date": "2026-01-20",
            },
        ]

        result = prioritize_items(items)

        assert result[0]["item_type"] == "action"
        assert result[1]["item_type"] == "risk"
        assert result[2]["item_type"] == "issue"
        assert result[3]["item_type"] == "decision"

    def test_due_date_ascending_within_type(self):
        """Items of same type sorted by due_date ascending."""
        items = [
            {
                "id": "1",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-25",
            },
            {
                "id": "2",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-20",
            },
            {
                "id": "3",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-22",
            },
        ]

        result = prioritize_items(items)

        assert result[0]["id"] == "2"  # 01-20
        assert result[1]["id"] == "3"  # 01-22
        assert result[2]["id"] == "1"  # 01-25

    def test_null_due_dates_last(self):
        """Items without due date sorted last."""
        items = [
            {"id": "1", "is_overdue": False, "item_type": "action", "due_date": None},
            {
                "id": "2",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-20",
            },
            {"id": "3", "is_overdue": False, "item_type": "action", "due_date": None},
        ]

        result = prioritize_items(items)

        assert result[0]["id"] == "2"  # Has due date
        assert result[1]["id"] in ["1", "3"]  # No due date
        assert result[2]["id"] in ["1", "3"]

    def test_max_items_truncation(self):
        """Result truncated to max_items."""
        items = [
            {
                "id": str(i),
                "is_overdue": False,
                "item_type": "action",
                "due_date": f"2026-01-{20+i:02d}",
            }
            for i in range(15)
        ]

        result = prioritize_items(items, max_items=5)

        assert len(result) == 5

    def test_is_new_marking_with_last_meeting_date(self):
        """Items created after last_meeting_date marked as is_new."""
        items = [
            {
                "id": "1",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-25",
                "created_at": "2026-01-10T10:00:00",
            },
            {
                "id": "2",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-20",
                "created_at": "2026-01-16T10:00:00",
            },
            {
                "id": "3",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-22",
                "created_at": "2026-01-18T10:00:00",
            },
        ]

        last_meeting = datetime(2026, 1, 15, 12, 0, 0)
        result = prioritize_items(items, last_meeting_date=last_meeting)

        # Item 1 created before last meeting
        assert result[2]["is_new"] is False  # id=1 sorted last by date
        # Items 2, 3 created after last meeting
        assert result[0]["is_new"] is True
        assert result[1]["is_new"] is True

    def test_is_new_false_without_last_meeting_date(self):
        """All items have is_new=False when no last_meeting_date provided."""
        items = [
            {
                "id": "1",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-25",
                "created_at": "2026-01-18T10:00:00",
            },
        ]

        result = prioritize_items(items)

        assert result[0]["is_new"] is False

    def test_empty_items_list(self):
        """Empty input returns empty output."""
        result = prioritize_items([])
        assert result == []

    def test_combined_sort_order(self):
        """Test full sorting priority: overdue > type > due_date."""
        items = [
            {
                "id": "1",
                "is_overdue": False,
                "item_type": "risk",
                "due_date": "2026-01-20",
            },
            {
                "id": "2",
                "is_overdue": True,
                "item_type": "decision",
                "due_date": "2026-01-10",
            },
            {
                "id": "3",
                "is_overdue": True,
                "item_type": "action",
                "due_date": "2026-01-12",
            },
            {
                "id": "4",
                "is_overdue": False,
                "item_type": "action",
                "due_date": "2026-01-25",
            },
        ]

        result = prioritize_items(items)

        # Overdue items first, sorted by type
        assert result[0]["id"] == "3"  # Overdue action
        assert result[1]["id"] == "2"  # Overdue decision
        # Non-overdue, sorted by type then date
        assert result[2]["id"] == "4"  # action (type 0)
        assert result[3]["id"] == "1"  # risk (type 1)


class TestGenerateTalkingPoints:
    """Tests for generate_talking_points function."""

    def test_overdue_items_point(self):
        """Generates talking point for overdue items."""
        items = [
            {"id": "1", "is_overdue": True, "item_type": "action"},
            {"id": "2", "is_overdue": True, "item_type": "action"},
            {"id": "3", "is_overdue": False, "item_type": "action"},
        ]

        points = generate_talking_points(items)

        overdue_point = next(p for p in points if p.category == "overdue")
        assert "2 overdue items" in overdue_point.text

    def test_risk_items_point(self):
        """Generates talking point for risk items."""
        items = [
            {
                "id": "1",
                "is_overdue": False,
                "item_type": "risk",
                "description": "Resource availability concern",
            },
        ]

        points = generate_talking_points(items)

        risk_point = next(p for p in points if p.category == "risk")
        assert "Discuss risk:" in risk_point.text
        assert "Resource availability" in risk_point.text

    def test_risk_description_truncated(self):
        """Risk description truncated to 50 chars with ellipsis."""
        items = [
            {
                "id": "1",
                "is_overdue": False,
                "item_type": "risk",
                "description": "A" * 100,
            },
        ]

        points = generate_talking_points(items)

        risk_point = next(p for p in points if p.category == "risk")
        assert "..." in risk_point.text
        assert len(risk_point.text) < 100

    def test_new_items_point(self):
        """Generates talking point for new items."""
        items = [
            {"id": "1", "is_overdue": False, "item_type": "action", "is_new": True},
            {"id": "2", "is_overdue": False, "item_type": "action", "is_new": True},
            {"id": "3", "is_overdue": False, "item_type": "action", "is_new": False},
        ]

        points = generate_talking_points(items)

        new_point = next(p for p in points if p.category == "new_item")
        assert "2 new items" in new_point.text

    def test_general_fallback(self):
        """Falls back to general point when no specific criteria met."""
        items = [
            {"id": "1", "is_overdue": False, "item_type": "action", "is_new": False},
            {"id": "2", "is_overdue": False, "item_type": "action", "is_new": False},
        ]

        points = generate_talking_points(items)

        general_point = next((p for p in points if p.category == "general"), None)
        assert general_point is not None
        assert "action" in general_point.text.lower()

    def test_max_points_limit(self):
        """Output limited to max_points."""
        items = [
            {
                "id": "1",
                "is_overdue": True,
                "item_type": "risk",
                "description": "Risk 1",
                "is_new": True,
            },
            {
                "id": "2",
                "is_overdue": True,
                "item_type": "risk",
                "description": "Risk 2",
                "is_new": True,
            },
        ]

        points = generate_talking_points(items, max_points=2)

        assert len(points) <= 2

    def test_empty_items_generic_point(self):
        """Empty items returns generic 'no items' point."""
        points = generate_talking_points([])

        assert len(points) == 1
        assert points[0].category == "general"
        assert "No open items" in points[0].text

    def test_returns_talking_point_models(self):
        """Returns list of TalkingPoint models."""
        items = [
            {"id": "1", "is_overdue": True, "item_type": "action"},
        ]

        points = generate_talking_points(items)

        assert all(isinstance(p, TalkingPoint) for p in points)

    def test_singular_overdue_item(self):
        """Singular form for single overdue item."""
        items = [
            {"id": "1", "is_overdue": True, "item_type": "action"},
        ]

        points = generate_talking_points(items)

        overdue_point = next(p for p in points if p.category == "overdue")
        assert "1 overdue item" in overdue_point.text
        assert "items" not in overdue_point.text


class TestItemMatcher:
    """Tests for ItemMatcher class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock TursoClient."""
        db = MagicMock(spec=TursoClient)
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_get_items_for_prep_returns_matching_items(self, mock_db):
        """Returns items matching attendee emails."""
        mock_db.execute.return_value = MagicMock(
            rows=[
                (
                    "id1",
                    "meeting1",
                    "action",
                    "Complete design",
                    "alice@example.com",
                    "2026-01-25",
                    "open",
                    0.9,
                    "2026-01-10T10:00:00",
                ),
                (
                    "id2",
                    "meeting1",
                    "risk",
                    "Resource risk",
                    "bob@example.com",
                    None,
                    "open",
                    0.85,
                    "2026-01-12T10:00:00",
                ),
            ]
        )

        matcher = ItemMatcher(mock_db)
        items = await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com", "bob@example.com"],
            project_id="proj1",
        )

        assert len(items) == 2
        assert items[0]["id"] == "id1"
        assert items[0]["item_type"] == "action"
        assert items[1]["id"] == "id2"

    @pytest.mark.asyncio
    async def test_get_items_for_prep_computes_is_overdue(self, mock_db):
        """Computes is_overdue based on due_date."""
        # Set due_date in the past
        mock_db.execute.return_value = MagicMock(
            rows=[
                (
                    "id1",
                    "meeting1",
                    "action",
                    "Overdue task",
                    "alice@example.com",
                    "2020-01-01",
                    "open",
                    0.9,
                    "2020-01-01T10:00:00",
                ),
            ]
        )

        matcher = ItemMatcher(mock_db)
        items = await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
        )

        assert items[0]["is_overdue"] is True

    @pytest.mark.asyncio
    async def test_get_items_for_prep_not_overdue_for_future_date(self, mock_db):
        """is_overdue is False for future due dates."""
        mock_db.execute.return_value = MagicMock(
            rows=[
                (
                    "id1",
                    "meeting1",
                    "action",
                    "Future task",
                    "alice@example.com",
                    "2099-12-31",
                    "open",
                    0.9,
                    "2026-01-01T10:00:00",
                ),
            ]
        )

        matcher = ItemMatcher(mock_db)
        items = await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
        )

        assert items[0]["is_overdue"] is False

    @pytest.mark.asyncio
    async def test_get_items_for_prep_not_overdue_for_null_date(self, mock_db):
        """is_overdue is False for null due dates."""
        mock_db.execute.return_value = MagicMock(
            rows=[
                (
                    "id1",
                    "meeting1",
                    "action",
                    "No due date",
                    "alice@example.com",
                    None,
                    "open",
                    0.9,
                    "2026-01-01T10:00:00",
                ),
            ]
        )

        matcher = ItemMatcher(mock_db)
        items = await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
        )

        assert items[0]["is_overdue"] is False

    @pytest.mark.asyncio
    async def test_get_items_for_prep_empty_attendees(self, mock_db):
        """Returns empty list for empty attendee list."""
        matcher = ItemMatcher(mock_db)
        items = await matcher.get_items_for_prep(
            attendee_emails=[],
            project_id="proj1",
        )

        assert items == []
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_items_for_prep_uses_lookback_days(self, mock_db):
        """Query includes lookback_days parameter."""
        mock_db.execute.return_value = MagicMock(rows=[])

        matcher = ItemMatcher(mock_db)
        await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
            lookback_days=30,
        )

        # Check that the query includes the lookback days
        call_args = mock_db.execute.call_args
        query = call_args[0][0]
        assert "-30 days" in query

    @pytest.mark.asyncio
    async def test_get_items_for_prep_default_lookback(self, mock_db):
        """Default lookback is 90 days."""
        mock_db.execute.return_value = MagicMock(rows=[])

        matcher = ItemMatcher(mock_db)
        await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
        )

        call_args = mock_db.execute.call_args
        query = call_args[0][0]
        assert "-90 days" in query

    @pytest.mark.asyncio
    async def test_get_items_for_prep_no_results(self, mock_db):
        """Returns empty list when no items match."""
        mock_db.execute.return_value = MagicMock(rows=[])

        matcher = ItemMatcher(mock_db)
        items = await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
        )

        assert items == []


class TestItemMatcherIntegration:
    """Integration tests using real SQLite database."""

    @pytest.fixture
    async def db_with_items(self, tmp_path: Path):
        """Create database with test items."""
        db_path = tmp_path / "test_items.db"
        db = TursoClient(url=f"file:{db_path}")
        await db.connect()

        # Create the raid_items_projection table
        await db.execute("""
            CREATE TABLE raid_items_projection (
                id TEXT PRIMARY KEY,
                meeting_id TEXT,
                item_type TEXT,
                description TEXT,
                owner TEXT,
                due_date TEXT,
                status TEXT,
                confidence REAL,
                created_at TEXT
            )
        """)

        # Insert test items - use individual inserts for line length compliance
        await db.execute(
            "INSERT INTO raid_items_projection VALUES "
            "('item1', 'meeting1', 'action', 'Complete design doc', "
            "'alice@example.com', '2026-01-25', 'open', 0.9, '2026-01-10T10:00:00')"
        )
        await db.execute(
            "INSERT INTO raid_items_projection VALUES "
            "('item2', 'meeting1', 'risk', 'Resource availability', "
            "'bob@example.com', NULL, 'open', 0.85, '2026-01-12T10:00:00')"
        )
        await db.execute(
            "INSERT INTO raid_items_projection VALUES "
            "('item3', 'meeting2', 'action', 'Review PR', "
            "'charlie@example.com', '2026-01-20', 'open', 0.9, '2026-01-15T10:00:00')"
        )
        await db.execute(
            "INSERT INTO raid_items_projection VALUES "
            "('item4', 'meeting1', 'action', 'Closed task', "
            "'alice@example.com', '2026-01-15', 'completed', 0.9, "
            "'2026-01-08T10:00:00')"
        )
        await db.execute(
            "INSERT INTO raid_items_projection VALUES "
            "('item5', 'meeting3', 'issue', 'Old issue', "
            "'alice@example.com', '2025-01-01', 'open', 0.8, '2024-01-01T10:00:00')"
        )

        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_filters_by_attendee_email(self, db_with_items):
        """Only returns items where owner is in attendee list."""
        matcher = ItemMatcher(db_with_items)
        items = await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
        )

        # Should include alice's items and items from meetings with alice
        item_ids = {i["id"] for i in items}
        assert "item1" in item_ids  # alice's item
        assert "item2" in item_ids  # from same meeting as alice
        # item4 excluded (closed)
        # item5 excluded (too old, outside 90 day lookback)

    @pytest.mark.asyncio
    async def test_excludes_closed_items(self, db_with_items):
        """Does not return items with closed status."""
        matcher = ItemMatcher(db_with_items)
        items = await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
        )

        item_ids = {i["id"] for i in items}
        assert "item4" not in item_ids  # completed status

    @pytest.mark.asyncio
    async def test_respects_lookback_days(self, db_with_items):
        """Only returns items within lookback period."""
        matcher = ItemMatcher(db_with_items)
        items = await matcher.get_items_for_prep(
            attendee_emails=["alice@example.com"],
            project_id="proj1",
            lookback_days=90,
        )

        item_ids = {i["id"] for i in items}
        # item5 is from 2024, outside 90-day lookback from 2026
        assert "item5" not in item_ids
