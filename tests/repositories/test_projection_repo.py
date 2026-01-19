"""Tests for ProjectionRepository."""

from pathlib import Path

import pytest

from src.db.turso import TursoClient
from src.repositories.projection_repo import ProjectionRepository
from src.search.schemas import (
    MeetingProjection,
    RaidItemProjection,
    TranscriptProjection,
)


@pytest.fixture
async def db_client(tmp_path: Path):
    """Create a temp file database client for testing."""
    db_path = tmp_path / "test_projections.db"
    client = TursoClient(url=f"file:{db_path}")
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
async def repo(db_client: TursoClient):
    """Create ProjectionRepository with initialized tables."""
    repo = ProjectionRepository(db_client)
    await repo.initialize()
    return repo


@pytest.mark.asyncio
async def test_initialize_creates_tables(db_client: TursoClient):
    """Initialize should create all projection tables."""
    repo = ProjectionRepository(db_client)
    await repo.initialize()

    # Verify tables exist
    result = await db_client.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    table_names = [row[0] for row in result.rows]

    assert "meetings_projection" in table_names
    assert "raid_items_projection" in table_names
    assert "transcripts_projection" in table_names


@pytest.mark.asyncio
async def test_initialize_creates_fts_tables(db_client: TursoClient):
    """Initialize should create FTS5 virtual tables."""
    repo = ProjectionRepository(db_client)
    await repo.initialize()

    # Verify FTS tables exist (they appear as tables in sqlite_master)
    result = await db_client.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts%'"
    )
    fts_table_names = [row[0] for row in result.rows]

    assert "raid_items_fts" in fts_table_names
    assert "transcripts_fts" in fts_table_names


@pytest.mark.asyncio
async def test_upsert_meeting_creates(repo: ProjectionRepository):
    """upsert_meeting should create a new meeting projection."""
    meeting = MeetingProjection(
        id="meeting-123",
        title="Sprint Planning",
        date="2026-01-19",
        participant_count=5,
    )

    await repo.upsert_meeting(meeting)

    result = await repo.get_meeting("meeting-123")
    assert result is not None
    assert result.id == "meeting-123"
    assert result.title == "Sprint Planning"
    assert result.date == "2026-01-19"
    assert result.participant_count == 5


@pytest.mark.asyncio
async def test_upsert_meeting_updates(repo: ProjectionRepository):
    """upsert_meeting should update an existing meeting projection."""
    meeting = MeetingProjection(
        id="meeting-123",
        title="Sprint Planning",
        date="2026-01-19",
        participant_count=5,
    )
    await repo.upsert_meeting(meeting)

    # Update the meeting
    updated_meeting = MeetingProjection(
        id="meeting-123",
        title="Sprint Planning (Updated)",
        date="2026-01-20",
        participant_count=7,
    )
    await repo.upsert_meeting(updated_meeting)

    result = await repo.get_meeting("meeting-123")
    assert result is not None
    assert result.title == "Sprint Planning (Updated)"
    assert result.date == "2026-01-20"
    assert result.participant_count == 7


@pytest.mark.asyncio
async def test_get_meeting_not_found(repo: ProjectionRepository):
    """get_meeting should return None for nonexistent meeting."""
    result = await repo.get_meeting("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_upsert_raid_item_creates(repo: ProjectionRepository):
    """upsert_raid_item should create a new RAID item projection."""
    item = RaidItemProjection(
        id="action-123",
        meeting_id="meeting-123",
        item_type="action",
        description="Complete the API integration",
        owner="John Doe",
        due_date="2026-01-25",
        status="pending",
        confidence=0.85,
    )

    await repo.upsert_raid_item(item)

    result = await repo.get_raid_item("action-123")
    assert result is not None
    assert result.id == "action-123"
    assert result.item_type == "action"
    assert result.description == "Complete the API integration"
    assert result.owner == "John Doe"
    assert result.confidence == 0.85


@pytest.mark.asyncio
async def test_upsert_raid_item_updates(repo: ProjectionRepository):
    """upsert_raid_item should update an existing RAID item."""
    item = RaidItemProjection(
        id="action-123",
        meeting_id="meeting-123",
        item_type="action",
        description="Complete the API integration",
        owner="John Doe",
        status="pending",
        confidence=0.85,
    )
    await repo.upsert_raid_item(item)

    # Update the item
    updated_item = RaidItemProjection(
        id="action-123",
        meeting_id="meeting-123",
        item_type="action",
        description="Complete the API integration (revised)",
        owner="Jane Doe",
        status="pending",
        confidence=0.9,
    )
    await repo.upsert_raid_item(updated_item)

    result = await repo.get_raid_item("action-123")
    assert result is not None
    assert result.description == "Complete the API integration (revised)"
    assert result.owner == "Jane Doe"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_get_raid_item_not_found(repo: ProjectionRepository):
    """get_raid_item should return None for nonexistent item."""
    result = await repo.get_raid_item("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_insert_transcript_utterance(repo: ProjectionRepository):
    """insert_transcript_utterance should insert a new utterance."""
    utterance = TranscriptProjection(
        meeting_id="meeting-123",
        speaker="Alice",
        text="Let's discuss the API integration timeline.",
        start_time=120.5,
    )

    await repo.insert_transcript_utterance(utterance)

    # Verify by querying directly
    result = await repo._db.execute(
        "SELECT meeting_id, speaker, text, start_time FROM transcripts_projection"
    )
    assert len(result.rows) == 1
    assert result.rows[0][0] == "meeting-123"
    assert result.rows[0][1] == "Alice"
    assert result.rows[0][2] == "Let's discuss the API integration timeline."
    assert result.rows[0][3] == 120.5


@pytest.mark.asyncio
async def test_update_item_status_success(repo: ProjectionRepository):
    """update_item_status should update status and return True."""
    item = RaidItemProjection(
        id="action-123",
        meeting_id="meeting-123",
        item_type="action",
        description="Complete task",
        status="pending",
    )
    await repo.upsert_raid_item(item)

    result = await repo.update_item_status("action-123", "completed")

    assert result is True
    updated = await repo.get_raid_item("action-123")
    assert updated is not None
    assert updated.status == "completed"


@pytest.mark.asyncio
async def test_update_item_status_not_found(repo: ProjectionRepository):
    """update_item_status should return False for nonexistent item."""
    result = await repo.update_item_status("nonexistent-id", "completed")
    assert result is False


@pytest.mark.asyncio
async def test_fts_sync_raid_items(repo: ProjectionRepository):
    """FTS5 should automatically sync with raid_items_projection via triggers."""
    # Insert a RAID item
    item = RaidItemProjection(
        id="action-456",
        meeting_id="meeting-789",
        item_type="action",
        description="Review the database migration plan",
        owner="Bob Smith",
        status="pending",
    )
    await repo.upsert_raid_item(item)

    # Search using FTS
    results = await repo.search_raid_items("database migration")

    assert len(results) == 1
    assert results[0].id == "action-456"
    assert results[0].description == "Review the database migration plan"


@pytest.mark.asyncio
async def test_fts_sync_transcripts(repo: ProjectionRepository):
    """FTS5 should automatically sync with transcripts_projection via triggers."""
    # Insert a transcript utterance
    utterance = TranscriptProjection(
        meeting_id="meeting-123",
        speaker="Alice",
        text="We need to finalize the deployment schedule.",
        start_time=60.0,
    )
    await repo.insert_transcript_utterance(utterance)

    # Search using FTS
    results = await repo.search_transcripts("deployment schedule")

    assert len(results) == 1
    assert results[0].text == "We need to finalize the deployment schedule."


@pytest.mark.asyncio
async def test_clear_all_projections(repo: ProjectionRepository):
    """clear_all_projections should delete all data from projection tables."""
    # Add data to all tables
    await repo.upsert_meeting(MeetingProjection(id="m1", title="Meeting 1"))
    await repo.upsert_raid_item(
        RaidItemProjection(
            id="r1", meeting_id="m1", item_type="action", description="Task"
        )
    )
    await repo.insert_transcript_utterance(
        TranscriptProjection(meeting_id="m1", text="Hello")
    )

    # Clear all
    await repo.clear_all_projections()

    # Verify all tables are empty
    meeting = await repo.get_meeting("m1")
    raid_item = await repo.get_raid_item("r1")
    transcripts = await repo._db.execute("SELECT COUNT(*) FROM transcripts_projection")

    assert meeting is None
    assert raid_item is None
    assert transcripts.rows[0][0] == 0


@pytest.mark.asyncio
async def test_fts_search_multiple_results(repo: ProjectionRepository):
    """FTS search should return multiple matching items ranked by relevance."""
    # Insert multiple items
    items = [
        RaidItemProjection(
            id="a1",
            meeting_id="m1",
            item_type="action",
            description="Review API documentation",
            owner="Alice",
        ),
        RaidItemProjection(
            id="a2",
            meeting_id="m1",
            item_type="action",
            description="Update API endpoints",
            owner="Bob",
        ),
        RaidItemProjection(
            id="a3",
            meeting_id="m1",
            item_type="decision",
            description="Use REST for the new API",
            owner="Charlie",
        ),
        RaidItemProjection(
            id="a4",
            meeting_id="m1",
            item_type="risk",
            description="Database performance issues",
            owner="Dave",
        ),
    ]

    for item in items:
        await repo.upsert_raid_item(item)

    # Search for "API"
    results = await repo.search_raid_items("API")

    assert len(results) == 3  # Should match a1, a2, a3 (not a4)
    result_ids = [r.id for r in results]
    assert "a1" in result_ids
    assert "a2" in result_ids
    assert "a3" in result_ids
    assert "a4" not in result_ids


@pytest.mark.asyncio
async def test_rebuild_fts_indexes(repo: ProjectionRepository):
    """rebuild_fts_indexes should rebuild FTS5 indexes from content tables."""
    # Insert an item
    item = RaidItemProjection(
        id="action-rebuild",
        meeting_id="meeting-1",
        item_type="action",
        description="Test rebuild functionality",
    )
    await repo.upsert_raid_item(item)

    # Rebuild indexes (should not fail)
    await repo.rebuild_fts_indexes()

    # Verify search still works
    results = await repo.search_raid_items("rebuild functionality")
    assert len(results) == 1
    assert results[0].id == "action-rebuild"
