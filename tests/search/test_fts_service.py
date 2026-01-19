"""Tests for FTSService full-text search."""

from pathlib import Path

import pytest

from src.db.turso import TursoClient
from src.search.fts_service import FTSService, parse_search_query


@pytest.fixture
async def db_client(tmp_path: Path):
    """Create a temp file database client for testing."""
    db_path = tmp_path / "test_fts.db"
    client = TursoClient(url=f"file:{db_path}")
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
async def db_with_fts(db_client: TursoClient):
    """Create required tables and FTS5 indexes."""
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

    # Create transcripts_projection table
    await db_client.execute("""
        CREATE TABLE IF NOT EXISTS transcripts_projection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id TEXT NOT NULL,
            speaker TEXT,
            text TEXT NOT NULL,
            start_time REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create FTS5 for RAID items
    await db_client.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS raid_items_fts USING fts5(
            description,
            owner,
            content='raid_items_projection',
            content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)

    # Create FTS5 for transcripts
    await db_client.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS transcripts_fts USING fts5(
            speaker,
            text,
            content='transcripts_projection',
            content_rowid='id',
            tokenize='porter unicode61'
        )
    """)

    # Create triggers for RAID items FTS sync
    await db_client.execute("""
        CREATE TRIGGER IF NOT EXISTS raid_items_ai
        AFTER INSERT ON raid_items_projection
        BEGIN
            INSERT INTO raid_items_fts(rowid, description, owner)
            VALUES (new.rowid, new.description, new.owner);
        END
    """)

    # Create triggers for transcripts FTS sync
    await db_client.execute("""
        CREATE TRIGGER IF NOT EXISTS transcripts_ai
        AFTER INSERT ON transcripts_projection
        BEGIN
            INSERT INTO transcripts_fts(rowid, speaker, text)
            VALUES (new.id, new.speaker, new.text);
        END
    """)

    return db_client


@pytest.fixture
async def seeded_db(db_with_fts: TursoClient):
    """Seed database with test data."""
    # Insert RAID items
    raid_items = [
        (
            "item-1",
            "meeting-1",
            "action",
            "Review the API documentation before deadline",
            "Alice",
        ),
        ("item-2", "meeting-1", "action", "Deploy new database migration", "Bob"),
        ("item-3", "meeting-2", "risk", "API rate limiting may cause issues", "Alice"),
        ("item-4", "meeting-2", "issue", "Production server running slow", "Charlie"),
        (
            "item-5",
            "meeting-3",
            "decision",
            "Use PostgreSQL for the new service",
            "Bob",
        ),
    ]

    for item_id, meeting_id, item_type, description, owner in raid_items:
        await db_with_fts.execute(
            """
            INSERT INTO raid_items_projection
                (id, meeting_id, item_type, description, owner)
            VALUES (?, ?, ?, ?, ?)
            """,
            [item_id, meeting_id, item_type, description, owner],
        )

    # Insert transcript utterances
    transcripts = [
        ("meeting-1", "Alice", "We need to discuss the API integration strategy"),
        ("meeting-1", "Bob", "I think we should prioritize the deadline next week"),
        (
            "meeting-2",
            "Charlie",
            "The production deployment is causing performance issues",
        ),
        ("meeting-2", "Alice", "Let's review the metrics before making changes"),
        ("meeting-3", "Bob", "The API documentation needs updating"),
    ]

    for meeting_id, speaker, text in transcripts:
        await db_with_fts.execute(
            """
            INSERT INTO transcripts_projection (meeting_id, speaker, text)
            VALUES (?, ?, ?)
            """,
            [meeting_id, speaker, text],
        )

    return db_with_fts


@pytest.fixture
async def fts_service(seeded_db: TursoClient):
    """Create FTSService with seeded database."""
    return FTSService(seeded_db)


class TestParseSearchQuery:
    """Tests for parse_search_query function."""

    def test_extracts_filters_correctly(self):
        """Filters like type:action are extracted."""
        result = parse_search_query("type:action owner:john api bug")
        assert result.filters == {"type": "action", "owner": "john"}
        assert result.keywords == "api bug"

    def test_handles_query_with_no_filters(self):
        """Query without filters returns empty filters dict."""
        result = parse_search_query("api documentation review")
        assert result.filters == {}
        assert result.keywords == "api documentation review"

    def test_handles_query_with_only_filters(self):
        """Query with only filters returns empty keywords."""
        result = parse_search_query("type:action status:pending")
        assert result.filters == {"type": "action", "status": "pending"}
        assert result.keywords == ""

    def test_handles_empty_query(self):
        """Empty query returns empty result."""
        result = parse_search_query("")
        assert result.filters == {}
        assert result.keywords == ""

    def test_normalizes_multiple_spaces(self):
        """Multiple spaces in keywords are normalized."""
        result = parse_search_query("type:action  api   bug")
        assert result.keywords == "api bug"

    def test_handles_filter_with_underscore(self):
        """Filters with underscores are handled."""
        result = parse_search_query("item_type:action search term")
        assert result.filters == {"item_type": "action"}
        assert result.keywords == "search term"


class TestFTSServiceSearch:
    """Tests for FTSService.search method."""

    @pytest.mark.asyncio
    async def test_search_returns_results_from_raid_items(
        self, fts_service: FTSService
    ):
        """Search returns results from RAID items."""
        response = await fts_service.search("API")
        assert len(response.raid_items) > 0
        # Should find items with "API" in description
        assert any(
            "API" in r.snippet or "api" in r.snippet.lower()
            for r in response.raid_items
        )

    @pytest.mark.asyncio
    async def test_search_returns_results_from_transcripts(
        self, fts_service: FTSService
    ):
        """Search returns results from transcripts."""
        response = await fts_service.search("deadline")
        assert len(response.transcripts) > 0
        assert response.transcripts[0].source == "transcript"

    @pytest.mark.asyncio
    async def test_search_with_type_filter_narrows_results(
        self, fts_service: FTSService
    ):
        """Filter type:action only returns action items."""
        response = await fts_service.search("type:action API")
        for result in response.raid_items:
            assert result.item_type == "action"

    @pytest.mark.asyncio
    async def test_search_with_owner_filter(self, fts_service: FTSService):
        """Filter owner:name filters by owner."""
        response = await fts_service.search("owner:Alice API")
        # Should only return Alice's items
        assert len(response.raid_items) > 0
        # Note: owner filter uses LIKE, so partial match works

    @pytest.mark.asyncio
    async def test_search_returns_empty_results_for_no_match(
        self, fts_service: FTSService
    ):
        """Search returns empty results when nothing matches."""
        response = await fts_service.search("xyznonexistent123")
        assert response.total_results == 0
        assert len(response.raid_items) == 0
        assert len(response.transcripts) == 0

    @pytest.mark.asyncio
    async def test_search_handles_special_characters_gracefully(
        self, fts_service: FTSService
    ):
        """Search handles special characters without error."""
        # These shouldn't crash
        response = await fts_service.search('API "test"')
        assert response is not None

        response = await fts_service.search("API*")
        assert response is not None

        response = await fts_service.search("(API OR documentation)")
        assert response is not None

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, fts_service: FTSService):
        """Search respects the limit parameter."""
        response = await fts_service.search("API", limit=1)
        assert len(response.raid_items) <= 1
        assert len(response.transcripts) <= 1

    @pytest.mark.asyncio
    async def test_search_results_include_snippets(self, fts_service: FTSService):
        """Search results include highlighted snippets."""
        response = await fts_service.search("API")
        if response.raid_items:
            # Snippets should be non-empty
            assert response.raid_items[0].snippet
            # May contain mark tags for highlighting
            # (depends on FTS5 result)

    @pytest.mark.asyncio
    async def test_search_empty_keywords_returns_no_results(
        self, fts_service: FTSService
    ):
        """Search with only filters (no keywords) returns empty results."""
        response = await fts_service.search("type:action")
        # Can't do FTS MATCH without keywords
        assert response.total_results == 0

    @pytest.mark.asyncio
    async def test_search_speaker_filter_for_transcripts(self, fts_service: FTSService):
        """Speaker filter narrows transcript results."""
        response = await fts_service.search("speaker:Alice API")
        # Should only return transcripts from Alice
        for result in response.transcripts:
            assert result.speaker is None or "Alice" in (result.speaker or "")
