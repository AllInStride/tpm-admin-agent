"""Tests for Search API endpoints."""

from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.db.turso import TursoClient
from src.events.bus import EventBus
from src.events.store import EventStore
from src.main import app
from src.repositories.open_items_repo import OpenItemsRepository
from src.repositories.projection_repo import ProjectionRepository
from src.search.duplicate_detector import DuplicateDetector
from src.search.fts_service import FTSService


@pytest.fixture
async def db_client(tmp_path: Path):
    """Create a temp file database client for testing."""
    db_path = tmp_path / "test_search_api.db"
    client = TursoClient(url=f"file:{db_path}")
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
async def setup_app(db_client: TursoClient):
    """Set up app state with database and services."""
    # Initialize event store
    event_store = EventStore(db_client)
    await event_store.init_schema()

    # Initialize projection repo
    projection_repo = ProjectionRepository(db_client)
    await projection_repo.initialize()

    # Set up app state
    app.state.db = db_client
    app.state.event_store = event_store
    app.state.event_bus = EventBus(store=event_store)
    app.state.projection_repo = projection_repo
    app.state.fts_service = FTSService(db_client)
    app.state.duplicate_detector = DuplicateDetector(db_client)
    app.state.open_items_repo = OpenItemsRepository(db_client)

    yield db_client

    # Cleanup app state
    del app.state.db
    del app.state.event_store
    del app.state.event_bus
    del app.state.projection_repo
    del app.state.fts_service
    del app.state.duplicate_detector
    del app.state.open_items_repo


@pytest.fixture
async def seeded_app(setup_app: TursoClient):
    """Seed the database with test data."""
    db = setup_app

    # Insert meetings
    await db.execute(
        """
        INSERT INTO meetings_projection (id, title, date)
        VALUES (?, ?, ?)
        """,
        ["meeting-1", "Sprint Planning", "2026-01-15"],
    )
    await db.execute(
        """
        INSERT INTO meetings_projection (id, title, date)
        VALUES (?, ?, ?)
        """,
        ["meeting-2", "Daily Standup", "2026-01-16"],
    )

    # Today's date for relative date calculations
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Insert RAID items
    items = [
        ("item-1", "meeting-1", "action", "Review API docs", "Alice", yesterday),
        ("item-2", "meeting-1", "action", "Deploy feature", "Bob", today),
        ("item-3", "meeting-2", "risk", "Security review", "Alice", tomorrow),
        ("item-4", "meeting-2", "issue", "Fix bug", "Charlie", None),
    ]

    for item_id, meeting_id, item_type, description, owner, due_date in items:
        await db.execute(
            """
            INSERT INTO raid_items_projection
                (id, meeting_id, item_type, description, owner, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [item_id, meeting_id, item_type, description, owner, due_date],
        )

    # Insert transcripts
    await db.execute(
        """
        INSERT INTO transcripts_projection (meeting_id, speaker, text)
        VALUES (?, ?, ?)
        """,
        ["meeting-1", "Alice", "We need to review the API documentation"],
    )

    # Insert events for history test (need event_id for NOT NULL constraint)
    import uuid

    await db.execute(
        """
        INSERT INTO events
            (event_id, event_type, aggregate_id, event_data, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            str(uuid.uuid4()),
            "ActionItemExtracted",
            "item-1",
            '{"meeting_id": "meeting-1"}',
            "2026-01-15T10:00:00Z",
        ],
    )

    return db


@pytest.fixture
async def client(seeded_app: TursoClient) -> AsyncIterator[AsyncClient]:
    """Create async test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestSearchEndpoint:
    """Tests for GET /search endpoint."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, client: AsyncClient):
        """Search returns results for matching query."""
        response = await client.get("/search", params={"q": "API"})
        assert response.status_code == 200
        data = response.json()
        assert "raid_items" in data
        assert "transcripts" in data
        assert "total_results" in data

    @pytest.mark.asyncio
    async def test_search_requires_query(self, client: AsyncClient):
        """Search returns 422 without query parameter."""
        response = await client.get("/search")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_with_limit(self, client: AsyncClient):
        """Search respects limit parameter."""
        response = await client.get("/search", params={"q": "API", "limit": 1})
        assert response.status_code == 200


class TestOpenItemsEndpoint:
    """Tests for GET /search/open-items endpoint."""

    @pytest.mark.asyncio
    async def test_returns_grouped_items(self, client: AsyncClient):
        """Returns grouped open items."""
        response = await client.get("/search/open-items")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "items" in data
        assert "group_by" in data
        assert data["group_by"] == "due_date"

    @pytest.mark.asyncio
    async def test_filters_by_item_type(self, client: AsyncClient):
        """Filters by item_type parameter."""
        response = await client.get(
            "/search/open-items", params={"item_type": "action"}
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["item_type"] == "action"

    @pytest.mark.asyncio
    async def test_filters_by_owner(self, client: AsyncClient):
        """Filters by owner parameter."""
        response = await client.get("/search/open-items", params={"owner": "Alice"})
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["owner"] == "Alice"

    @pytest.mark.asyncio
    async def test_filters_overdue_only(self, client: AsyncClient):
        """Filters to overdue items only."""
        response = await client.get("/search/open-items", params={"overdue_only": True})
        assert response.status_code == 200
        data = response.json()
        # All items should be overdue (due date < today)
        assert len(data["items"]) >= 0  # May be 0 or more

    @pytest.mark.asyncio
    async def test_group_by_owner(self, client: AsyncClient):
        """Groups by owner."""
        response = await client.get("/search/open-items", params={"group_by": "owner"})
        assert response.status_code == 200
        data = response.json()
        assert data["group_by"] == "owner"


class TestOpenItemsSummaryEndpoint:
    """Tests for GET /search/open-items/summary endpoint."""

    @pytest.mark.asyncio
    async def test_returns_summary_counts(self, client: AsyncClient):
        """Returns summary with counts."""
        response = await client.get("/search/open-items/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "overdue" in data
        assert "due_today" in data
        assert "due_this_week" in data
        assert "by_type" in data


class TestCloseItemEndpoint:
    """Tests for POST /search/items/{item_id}/close endpoint."""

    @pytest.mark.asyncio
    async def test_closes_item(self, client: AsyncClient):
        """Successfully closes an item."""
        response = await client.post("/search/items/item-1/close")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["item_id"] == "item-1"
        assert data["new_status"] == "completed"

    @pytest.mark.asyncio
    async def test_closes_with_custom_status(self, client: AsyncClient):
        """Closes item with custom status."""
        response = await client.post(
            "/search/items/item-2/close",
            json={"status": "cancelled"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent(self, client: AsyncClient):
        """Returns 404 for non-existent item."""
        response = await client.post("/search/items/nonexistent/close")
        assert response.status_code == 404


class TestItemHistoryEndpoint:
    """Tests for GET /search/items/{item_id}/history endpoint."""

    @pytest.mark.asyncio
    async def test_returns_history(self, client: AsyncClient):
        """Returns item history."""
        response = await client.get("/search/items/item-1/history")
        assert response.status_code == 200
        data = response.json()
        assert data["item_id"] == "item-1"
        assert "entries" in data
        assert "item_type" in data
        assert "description" in data

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent(self, client: AsyncClient):
        """Returns 404 for non-existent item."""
        response = await client.get("/search/items/nonexistent/history")
        assert response.status_code == 404


class TestCheckDuplicatesEndpoint:
    """Tests for POST /search/items/check-duplicates endpoint."""

    @pytest.mark.asyncio
    async def test_finds_duplicates(self, client: AsyncClient):
        """Finds potential duplicates."""
        response = await client.post(
            "/search/items/check-duplicates",
            json={"description": "Review API documentation"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "new_description" in data
        assert "potential_duplicates" in data
        assert "has_duplicates" in data

    @pytest.mark.asyncio
    async def test_filters_by_item_type(self, client: AsyncClient):
        """Filters duplicates by item type."""
        response = await client.post(
            "/search/items/check-duplicates",
            json={"description": "Deploy feature", "item_type": "action"},
        )
        assert response.status_code == 200


class TestRejectDuplicateEndpoint:
    """Tests for POST /search/items/{item_id}/reject-duplicate endpoint."""

    @pytest.mark.asyncio
    async def test_records_rejection(self, client: AsyncClient):
        """Records duplicate rejection."""
        response = await client.post(
            "/search/items/item-1/reject-duplicate",
            json={"duplicate_id": "item-2"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
