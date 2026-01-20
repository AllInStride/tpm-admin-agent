"""Tests for OpenItemsRepository."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.db.turso import TursoClient
from src.repositories.open_items_repo import OpenItemsRepository
from src.search.open_items import OpenItemFilter


@pytest.fixture
async def db_client(tmp_path: Path):
    """Create a temp file database client for testing."""
    db_path = tmp_path / "test_open_items.db"
    client = TursoClient(url=f"file:{db_path}")
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
async def db_with_tables(db_client: TursoClient):
    """Create required tables directly (not depending on 07-01)."""
    # Create raid_items_projection table
    await db_client.execute("""
        CREATE TABLE IF NOT EXISTS raid_items_projection (
            id TEXT PRIMARY KEY,
            meeting_id TEXT NOT NULL,
            item_type TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'pending',
            confidence REAL DEFAULT 1.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create meetings_projection table for history tests
    await db_client.execute("""
        CREATE TABLE IF NOT EXISTS meetings_projection (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT,
            participant_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create events table for history tests
    await db_client.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            aggregate_id TEXT,
            event_data TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    return db_client


@pytest.fixture
async def repo(db_with_tables: TursoClient):
    """Create OpenItemsRepository with initialized tables."""
    return OpenItemsRepository(db_with_tables)


@pytest.fixture
async def seeded_repo(db_with_tables: TursoClient):
    """Create repo with test data seeded."""
    repo = OpenItemsRepository(db_with_tables)

    # Use UTC dates consistently with SQLite's date('now') which returns UTC
    # Using larger offsets to avoid timezone edge cases

    now_utc = datetime.now(UTC)
    today = now_utc.strftime("%Y-%m-%d")
    two_days_ago = (now_utc - timedelta(days=2)).strftime("%Y-%m-%d")
    in_two_days = (now_utc + timedelta(days=2)).strftime("%Y-%m-%d")
    in_five_days = (now_utc + timedelta(days=5)).strftime("%Y-%m-%d")

    # Insert test data
    test_items = [
        # Clearly overdue (2 days ago)
        (
            "item-1",
            "meeting-1",
            "action",
            "Review PR",
            "Alice",
            two_days_ago,
            "pending",
        ),
        # Due today
        ("item-2", "meeting-1", "action", "Deploy feature", "Bob", today, "pending"),
        # Due this week (5 days)
        (
            "item-3",
            "meeting-2",
            "risk",
            "Security review",
            "Alice",
            in_five_days,
            "pending",
        ),
        # Due in 2 days (within week)
        ("item-4", "meeting-2", "issue", "Fix bug", "Charlie", in_two_days, "pending"),
        # Completed (should not appear)
        ("item-5", "meeting-1", "action", "Old task", "Bob", two_days_ago, "completed"),
        # No due date
        ("item-6", "meeting-3", "decision", "Approve design", "Alice", None, "pending"),
    ]

    for item in test_items:
        await db_with_tables.execute(
            """
            INSERT INTO raid_items_projection
            (id, meeting_id, item_type, description, owner, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            list(item),
        )

    # Insert meeting for history tests
    await db_with_tables.execute(
        """
        INSERT INTO meetings_projection (id, title, date)
        VALUES (?, ?, ?)
        """,
        ["meeting-1", "Sprint Planning", "2026-01-15"],
    )

    return repo


class TestGetSummary:
    """Tests for get_summary method."""

    @pytest.mark.asyncio
    async def test_summary_returns_correct_totals(
        self, seeded_repo: OpenItemsRepository
    ):
        """Summary returns correct total count of open items."""
        summary = await seeded_repo.get_summary()
        # 5 open items (item-5 is completed, not counted)
        assert summary.total == 5

    @pytest.mark.asyncio
    async def test_summary_returns_correct_overdue(
        self, seeded_repo: OpenItemsRepository
    ):
        """Summary correctly counts overdue items."""
        summary = await seeded_repo.get_summary()
        assert summary.overdue == 1  # item-1 is overdue

    @pytest.mark.asyncio
    async def test_summary_returns_correct_due_today(
        self, seeded_repo: OpenItemsRepository
    ):
        """Summary correctly counts items due today."""
        summary = await seeded_repo.get_summary()
        assert summary.due_today == 1  # item-2 is due today

    @pytest.mark.asyncio
    async def test_summary_returns_correct_due_this_week(
        self, seeded_repo: OpenItemsRepository
    ):
        """Summary correctly counts items due this week."""
        summary = await seeded_repo.get_summary()
        # item-3 (5 days) and item-4 (tomorrow) are due within 7 days
        assert summary.due_this_week == 2

    @pytest.mark.asyncio
    async def test_summary_by_type_counts(self, seeded_repo: OpenItemsRepository):
        """Summary returns correct counts by item type."""
        summary = await seeded_repo.get_summary()
        assert summary.by_type.get("action", 0) == 2  # item-1, item-2
        assert summary.by_type.get("risk", 0) == 1  # item-3
        assert summary.by_type.get("issue", 0) == 1  # item-4
        assert summary.by_type.get("decision", 0) == 1  # item-6


class TestGetItems:
    """Tests for get_items method."""

    @pytest.mark.asyncio
    async def test_get_items_no_filter(self, seeded_repo: OpenItemsRepository):
        """Get items with no filter returns all open items."""
        result = await seeded_repo.get_items()
        assert len(result.items) == 5
        # Should not include completed item
        item_ids = [item["id"] for item in result.items]
        assert "item-5" not in item_ids

    @pytest.mark.asyncio
    async def test_get_items_with_item_type_filter(
        self, seeded_repo: OpenItemsRepository
    ):
        """Filter by item_type returns correct items."""
        result = await seeded_repo.get_items(filter=OpenItemFilter(item_type="action"))
        assert len(result.items) == 2
        for item in result.items:
            assert item["item_type"] == "action"

    @pytest.mark.asyncio
    async def test_get_items_with_owner_filter(self, seeded_repo: OpenItemsRepository):
        """Filter by owner returns correct items."""
        result = await seeded_repo.get_items(filter=OpenItemFilter(owner="Alice"))
        assert len(result.items) == 3  # item-1, item-3, item-6
        for item in result.items:
            assert item["owner"] == "Alice"

    @pytest.mark.asyncio
    async def test_get_items_overdue_only(self, seeded_repo: OpenItemsRepository):
        """Filter overdue_only=True returns only overdue items."""
        result = await seeded_repo.get_items(filter=OpenItemFilter(overdue_only=True))
        assert len(result.items) == 1
        assert result.items[0]["id"] == "item-1"

    @pytest.mark.asyncio
    async def test_get_items_due_within_days(self, seeded_repo: OpenItemsRepository):
        """Filter due_within_days returns items due within N days."""
        result = await seeded_repo.get_items(filter=OpenItemFilter(due_within_days=7))
        # Should include: item-1 (overdue), item-2 (today), item-3 (5 days),
        # item-4 (tomorrow). NOT include: item-6 (no due date)
        assert len(result.items) == 4

    @pytest.mark.asyncio
    async def test_get_items_group_by_owner_orders_correctly(
        self, seeded_repo: OpenItemsRepository
    ):
        """group_by='owner' orders results by owner then due_date."""
        result = await seeded_repo.get_items(group_by="owner")
        assert result.group_by == "owner"
        # Check that items are ordered by owner
        owners = [item["owner"] for item in result.items]
        assert owners == sorted(owners, key=lambda x: (x is None, x or ""))

    @pytest.mark.asyncio
    async def test_get_items_group_by_item_type(self, seeded_repo: OpenItemsRepository):
        """group_by='item_type' orders results by item_type."""
        result = await seeded_repo.get_items(group_by="item_type")
        assert result.group_by == "item_type"

    @pytest.mark.asyncio
    async def test_get_items_includes_summary(self, seeded_repo: OpenItemsRepository):
        """get_items includes summary in response."""
        result = await seeded_repo.get_items()
        assert result.summary.total == 5


class TestCloseItem:
    """Tests for close_item method."""

    @pytest.mark.asyncio
    async def test_close_item_updates_status(self, seeded_repo: OpenItemsRepository):
        """close_item updates status and returns True."""
        updated = await seeded_repo.close_item("item-1")
        assert updated is True

        # Verify item is now closed
        summary = await seeded_repo.get_summary()
        assert summary.total == 4  # One less open item

    @pytest.mark.asyncio
    async def test_close_item_returns_false_for_nonexistent(
        self, seeded_repo: OpenItemsRepository
    ):
        """close_item returns False for non-existent item."""
        updated = await seeded_repo.close_item("nonexistent-id")
        assert updated is False

    @pytest.mark.asyncio
    async def test_close_item_custom_status(self, seeded_repo: OpenItemsRepository):
        """close_item can use custom status."""
        updated = await seeded_repo.close_item("item-1", new_status="cancelled")
        assert updated is True


class TestGetItemHistory:
    """Tests for get_item_history method."""

    @pytest.mark.asyncio
    async def test_get_item_history_returns_none_for_nonexistent(
        self, seeded_repo: OpenItemsRepository, db_with_tables: TursoClient
    ):
        """get_item_history returns None for non-existent item."""
        history = await seeded_repo.get_item_history("nonexistent-id")
        assert history is None

    @pytest.mark.asyncio
    async def test_get_item_history_returns_item_details(
        self, seeded_repo: OpenItemsRepository, db_with_tables: TursoClient
    ):
        """get_item_history returns item details."""
        # Add an event for item-1
        await db_with_tables.execute(
            """
            INSERT INTO events (event_type, aggregate_id, event_data, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            [
                "ActionItemExtracted",
                "item-1",
                '{"meeting_id": "meeting-1"}',
                "2026-01-15T10:00:00Z",
            ],
        )

        history = await seeded_repo.get_item_history("item-1")

        assert history is not None
        assert history.item_id == "item-1"
        assert history.item_type == "action"
        assert history.description == "Review PR"
        assert history.current_status == "pending"

    @pytest.mark.asyncio
    async def test_get_item_history_entries_chronological(
        self, seeded_repo: OpenItemsRepository, db_with_tables: TursoClient
    ):
        """get_item_history returns entries in chronological order."""
        # Add multiple events
        await db_with_tables.execute(
            """
            INSERT INTO events (event_type, aggregate_id, event_data, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            [
                "ActionItemExtracted",
                "item-1",
                '{"meeting_id": "meeting-1"}',
                "2026-01-15T10:00:00Z",
            ],
        )
        await db_with_tables.execute(
            """
            INSERT INTO events (event_type, aggregate_id, event_data, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            [
                "ActionItemUpdated",
                "item-1",
                '{"meeting_id": "meeting-1"}',
                "2026-01-16T14:00:00Z",
            ],
        )

        history = await seeded_repo.get_item_history("item-1")

        assert history is not None
        assert len(history.entries) == 2
        # Should be in chronological order
        assert history.entries[0].event_type == "ActionItemExtracted"
        assert history.entries[1].event_type == "ActionItemUpdated"
        assert history.entries[0].timestamp < history.entries[1].timestamp

    @pytest.mark.asyncio
    async def test_get_item_history_includes_meeting_context(
        self, seeded_repo: OpenItemsRepository, db_with_tables: TursoClient
    ):
        """get_item_history includes meeting context from projections."""
        # Add event that references meeting-1
        await db_with_tables.execute(
            """
            INSERT INTO events (event_type, aggregate_id, event_data, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            [
                "ActionItemExtracted",
                "item-1",
                '{"meeting_id": "meeting-1"}',
                "2026-01-15T10:00:00Z",
            ],
        )

        history = await seeded_repo.get_item_history("item-1")

        assert history is not None
        assert len(history.entries) == 1
        entry = history.entries[0]
        assert entry.meeting_id == "meeting-1"
        assert entry.meeting_title == "Sprint Planning"
        assert entry.meeting_date == "2026-01-15"

    @pytest.mark.asyncio
    async def test_classify_change_in_history(
        self, seeded_repo: OpenItemsRepository, db_with_tables: TursoClient
    ):
        """History entries have correct change_type classification."""
        # Add events with different types
        await db_with_tables.execute(
            """
            INSERT INTO events (event_type, aggregate_id, event_data, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            ["ActionItemExtracted", "item-1", "{}", "2026-01-15T10:00:00Z"],
        )
        await db_with_tables.execute(
            """
            INSERT INTO events (event_type, aggregate_id, event_data, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            ["ActionItemUpdated", "item-1", "{}", "2026-01-16T10:00:00Z"],
        )
        await db_with_tables.execute(
            """
            INSERT INTO events (event_type, aggregate_id, event_data, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            ["MeetingReferenced", "item-1", "{}", "2026-01-17T10:00:00Z"],
        )

        history = await seeded_repo.get_item_history("item-1")

        assert history is not None
        assert len(history.entries) == 3
        assert history.entries[0].change_type == "created"  # Extracted
        assert history.entries[1].change_type == "updated"  # Updated
        assert history.entries[2].change_type == "mentioned"  # Other
