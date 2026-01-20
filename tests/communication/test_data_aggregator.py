"""Tests for DataAggregator."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.communication.data_aggregator import DataAggregator


class MockResultSet:
    """Mock database result set."""

    def __init__(self, rows: list):
        self.rows = rows


@pytest.fixture
def mock_open_items_repo():
    """Create mock OpenItemsRepository."""
    repo = MagicMock()
    return repo


@pytest.fixture
def mock_projection_repo():
    """Create mock ProjectionRepository with database access."""
    repo = MagicMock()
    repo._db = MagicMock()
    return repo


@pytest.fixture
def aggregator(mock_open_items_repo, mock_projection_repo):
    """Create DataAggregator with mocks."""
    return DataAggregator(mock_open_items_repo, mock_projection_repo)


class TestDataAggregator:
    """Tests for DataAggregator class."""

    @pytest.mark.asyncio
    async def test_gather_for_status_basic(self, aggregator, mock_projection_repo):
        """Aggregator gathers basic status data."""
        # Setup mock responses
        mock_db = mock_projection_repo._db

        # Mock all database queries to return empty results
        mock_db.execute = AsyncMock(return_value=MockResultSet([]))

        now = datetime.now()
        since = now - timedelta(days=7)

        result = await aggregator.gather_for_status(
            project_id="project-1",
            since=since,
            until=now,
        )

        assert result.project_id == "project-1"
        assert result.time_period[0] == since
        assert result.time_period[1] == now
        assert result.completed_items == []
        assert result.new_items == []
        assert result.open_items == []
        assert result.item_velocity == 0
        assert result.overdue_count == 0

    @pytest.mark.asyncio
    async def test_gather_for_status_with_items(self, aggregator, mock_projection_repo):
        """Aggregator correctly categorizes items."""
        mock_db = mock_projection_repo._db

        now = datetime.now()
        since = now - timedelta(days=7)
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        last_week = (now - timedelta(days=10)).strftime("%Y-%m-%d")

        # Track which query is being made and return appropriate results
        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            query_lower = query.lower()

            # Completed items query (status IN closed statuses)
            if "status in" in query_lower and "completed" in query_lower:
                return MockResultSet(
                    [
                        (
                            "id-1",
                            "meeting-1",
                            "action",
                            "Done task",
                            "Alice",
                            yesterday,
                            "completed",
                            0.9,
                            yesterday,
                        ),
                    ]
                )

            # New items query (created_at in period)
            if "datetime(created_at)" in query_lower:
                return MockResultSet(
                    [
                        (
                            "id-2",
                            "meeting-1",
                            "decision",
                            "Decided X",
                            "Bob",
                            None,
                            "pending",
                            0.85,
                            yesterday,
                        ),
                        (
                            "id-3",
                            "meeting-1",
                            "action",
                            "New task",
                            "Alice",
                            tomorrow,
                            "pending",
                            0.9,
                            yesterday,
                        ),
                    ]
                )

            # Open items query (status NOT IN closed)
            if "status not in" in query_lower:
                return MockResultSet(
                    [
                        (
                            "id-3",
                            "meeting-1",
                            "action",
                            "New task",
                            "Alice",
                            tomorrow,
                            "pending",
                            0.9,
                            yesterday,
                        ),
                        (
                            "id-4",
                            "meeting-1",
                            "risk",
                            "Risk item",
                            None,
                            None,
                            "pending",
                            0.8,
                            yesterday,
                        ),
                        (
                            "id-5",
                            "meeting-1",
                            "issue",
                            "Issue item",
                            "Charlie",
                            None,
                            "pending",
                            0.75,
                            yesterday,
                        ),
                        (
                            "id-6",
                            "meeting-1",
                            "action",
                            "Overdue blocked task",
                            "Dave",
                            last_week,
                            "pending",
                            0.9,
                            yesterday,
                        ),
                    ]
                )

            # Meetings query
            if "meetings_projection" in query_lower:
                return MockResultSet(
                    [
                        ("m-1", "Daily Standup", yesterday, 5, yesterday),
                    ]
                )

            return MockResultSet([])

        mock_db.execute = mock_execute

        result = await aggregator.gather_for_status(
            project_id="project-1",
            since=since,
            until=now,
        )

        # Verify counts
        assert len(result.completed_items) == 1
        assert len(result.new_items) == 2
        assert len(result.open_items) == 4

        # Verify categorization
        assert len(result.decisions) == 1
        assert result.decisions[0]["item_type"] == "decision"

        assert len(result.risks) == 1
        assert result.risks[0]["item_type"] == "risk"

        assert len(result.issues) == 1
        assert result.issues[0]["item_type"] == "issue"

        # Blockers should include overdue item (with "blocked" in description)
        assert len(result.blockers) == 1
        assert "Overdue" in result.blockers[0]["description"]

        # Metrics
        assert result.item_velocity == 1 - 2  # completed - new = -1
        assert result.overdue_count == 1  # One overdue item
        assert len(result.meetings_held) == 1

    @pytest.mark.asyncio
    async def test_gather_uses_default_until(self, aggregator, mock_projection_repo):
        """Aggregator uses current time if until not provided."""
        mock_db = mock_projection_repo._db
        mock_db.execute = AsyncMock(return_value=MockResultSet([]))

        since = datetime.now() - timedelta(days=7)

        result = await aggregator.gather_for_status(
            project_id="project-1",
            since=since,
        )

        # until should be close to now
        assert result.time_period[1] is not None
        time_diff = datetime.now() - result.time_period[1]
        assert time_diff.total_seconds() < 5  # Within 5 seconds

    @pytest.mark.asyncio
    async def test_blocker_detection_by_overdue(self, aggregator, mock_projection_repo):
        """Items with past due dates are detected as blockers."""
        mock_db = mock_projection_repo._db

        now = datetime.now()
        past_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")

        async def mock_execute(query, params=None):
            if "status not in" in query.lower():
                return MockResultSet(
                    [
                        (
                            "id-1",
                            "m-1",
                            "action",
                            "Overdue task",
                            "Alice",
                            past_date,
                            "pending",
                            0.9,
                            past_date,
                        ),
                    ]
                )
            return MockResultSet([])

        mock_db.execute = mock_execute

        result = await aggregator.gather_for_status(
            project_id="project-1",
            since=now - timedelta(days=7),
            until=now,
        )

        # Overdue item should be a blocker
        assert len(result.blockers) == 1
        assert result.blockers[0]["id"] == "id-1"
        assert result.overdue_count == 1

    @pytest.mark.asyncio
    async def test_blocker_detection_by_keyword(self, aggregator, mock_projection_repo):
        """Items with 'blocked' in description are detected as blockers."""
        mock_db = mock_projection_repo._db

        now = datetime.now()
        future_date = (now + timedelta(days=5)).strftime("%Y-%m-%d")

        async def mock_execute(query, params=None):
            if "status not in" in query.lower():
                return MockResultSet(
                    [
                        (
                            "id-1",
                            "m-1",
                            "action",
                            "Task blocked by external team",
                            "Alice",
                            future_date,
                            "pending",
                            0.9,
                            now.strftime("%Y-%m-%d"),
                        ),
                    ]
                )
            return MockResultSet([])

        mock_db.execute = mock_execute

        result = await aggregator.gather_for_status(
            project_id="project-1",
            since=now - timedelta(days=7),
            until=now,
        )

        # Item with "blocked" in description should be a blocker even if not overdue
        assert len(result.blockers) == 1
        assert "blocked" in result.blockers[0]["description"].lower()
        assert result.overdue_count == 0  # Not overdue, just blocked

    @pytest.mark.asyncio
    async def test_velocity_calculation(self, aggregator, mock_projection_repo):
        """Velocity is correctly calculated as completed - new."""
        mock_db = mock_projection_repo._db

        now = datetime.now()
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            query_lower = query.lower()

            # Return 5 completed items
            if "status in" in query_lower and "completed" in query_lower:
                return MockResultSet(
                    [
                        (
                            f"completed-{i}",
                            "m-1",
                            "action",
                            f"Done {i}",
                            "Alice",
                            yesterday,
                            "completed",
                            0.9,
                            yesterday,
                        )
                        for i in range(5)
                    ]
                )

            # Return 3 new items
            if "datetime(created_at)" in query_lower:
                return MockResultSet(
                    [
                        (
                            f"new-{i}",
                            "m-1",
                            "action",
                            f"New {i}",
                            "Bob",
                            None,
                            "pending",
                            0.9,
                            yesterday,
                        )
                        for i in range(3)
                    ]
                )

            return MockResultSet([])

        mock_db.execute = mock_execute

        result = await aggregator.gather_for_status(
            project_id="project-1",
            since=now - timedelta(days=7),
            until=now,
        )

        # Velocity = completed (5) - new (3) = 2
        assert result.item_velocity == 2

    @pytest.mark.asyncio
    async def test_meetings_in_period(self, aggregator, mock_projection_repo):
        """Meetings within the period are correctly gathered."""
        mock_db = mock_projection_repo._db

        now = datetime.now()
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        two_days_ago = (now - timedelta(days=2)).strftime("%Y-%m-%d")

        async def mock_execute(query, params=None):
            if "meetings_projection" in query.lower():
                return MockResultSet(
                    [
                        ("m-1", "Daily Standup", yesterday, 5, yesterday),
                        ("m-2", "Sprint Planning", two_days_ago, 8, two_days_ago),
                    ]
                )
            return MockResultSet([])

        mock_db.execute = mock_execute

        result = await aggregator.gather_for_status(
            project_id="project-1",
            since=now - timedelta(days=7),
            until=now,
        )

        assert len(result.meetings_held) == 2
        assert result.meetings_held[0]["title"] == "Daily Standup"
        assert result.meetings_held[1]["title"] == "Sprint Planning"


class TestIsBlocker:
    """Tests for _is_blocker helper method."""

    @pytest.fixture
    def aggregator_for_helpers(self, mock_open_items_repo, mock_projection_repo):
        """Create aggregator for testing helper methods."""
        return DataAggregator(mock_open_items_repo, mock_projection_repo)

    def test_overdue_item_is_blocker(self, aggregator_for_helpers):
        """Overdue items are blockers."""
        now = datetime.now()
        past_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")

        item = {"due_date": past_date, "description": "Regular task"}
        assert aggregator_for_helpers._is_blocker(item, now) is True

    def test_future_item_not_blocker(self, aggregator_for_helpers):
        """Future items are not blockers by default."""
        now = datetime.now()
        future_date = (now + timedelta(days=5)).strftime("%Y-%m-%d")

        item = {"due_date": future_date, "description": "Regular task"}
        assert aggregator_for_helpers._is_blocker(item, now) is False

    def test_blocked_keyword_makes_blocker(self, aggregator_for_helpers):
        """Items with 'blocked' keyword are blockers."""
        now = datetime.now()
        future_date = (now + timedelta(days=5)).strftime("%Y-%m-%d")

        item = {"due_date": future_date, "description": "Task blocked by vendor"}
        assert aggregator_for_helpers._is_blocker(item, now) is True

    def test_block_keyword_makes_blocker(self, aggregator_for_helpers):
        """Items with 'block' keyword are blockers."""
        now = datetime.now()

        item = {"due_date": None, "description": "This is a blocking issue"}
        assert aggregator_for_helpers._is_blocker(item, now) is True


class TestIsOverdue:
    """Tests for _is_overdue helper method."""

    @pytest.fixture
    def aggregator_for_helpers(self, mock_open_items_repo, mock_projection_repo):
        """Create aggregator for testing helper methods."""
        return DataAggregator(mock_open_items_repo, mock_projection_repo)

    def test_past_date_is_overdue(self, aggregator_for_helpers):
        """Past due dates are overdue."""
        now = datetime.now()
        past_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        item = {"due_date": past_date}
        assert aggregator_for_helpers._is_overdue(item, now) is True

    def test_future_date_not_overdue(self, aggregator_for_helpers):
        """Future due dates are not overdue."""
        now = datetime.now()
        future_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        item = {"due_date": future_date}
        assert aggregator_for_helpers._is_overdue(item, now) is False

    def test_today_not_overdue(self, aggregator_for_helpers):
        """Today's date is not overdue."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        item = {"due_date": today}
        assert aggregator_for_helpers._is_overdue(item, now) is False

    def test_no_due_date_not_overdue(self, aggregator_for_helpers):
        """Items without due dates are not overdue."""
        now = datetime.now()

        item = {"due_date": None}
        assert aggregator_for_helpers._is_overdue(item, now) is False

    def test_various_date_formats(self, aggregator_for_helpers):
        """Different date formats are handled."""
        now = datetime.now()
        past = now - timedelta(days=5)

        formats = [
            past.strftime("%Y-%m-%d"),
            past.strftime("%Y-%m-%d %H:%M:%S"),
            past.strftime("%Y-%m-%dT%H:%M:%S"),
        ]

        for date_str in formats:
            item = {"due_date": date_str}
            assert (
                aggregator_for_helpers._is_overdue(item, now) is True
            ), f"Failed for format: {date_str}"
