"""Tests for ProjectionBuilder."""

from pathlib import Path
from uuid import uuid4

import pytest

from src.db.turso import TursoClient
from src.events.store import EventStore
from src.repositories.projection_repo import ProjectionRepository
from src.search.projections import ProjectionBuilder


@pytest.fixture
async def db_client(tmp_path: Path):
    """Create a temp file database client for testing."""
    db_path = tmp_path / "test_projections_builder.db"
    client = TursoClient(url=f"file:{db_path}")
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
async def event_store(db_client: TursoClient):
    """Create EventStore with initialized schema."""
    store = EventStore(db_client)
    await store.init_schema()
    return store


@pytest.fixture
async def projection_repo(db_client: TursoClient):
    """Create ProjectionRepository with initialized tables."""
    repo = ProjectionRepository(db_client)
    await repo.initialize()
    return repo


@pytest.fixture
def builder(event_store: EventStore, projection_repo: ProjectionRepository):
    """Create ProjectionBuilder instance."""
    return ProjectionBuilder(event_store, projection_repo)


@pytest.mark.asyncio
async def test_handle_meeting_created_event(
    builder: ProjectionBuilder, projection_repo: ProjectionRepository
):
    """handle_event should create meeting projection from MeetingCreated."""
    meeting_id = str(uuid4())
    event_data = {
        "event_type": "MeetingCreated",
        "aggregate_id": meeting_id,
        "data": {
            "title": "Sprint Planning",
            "meeting_date": "2026-01-19T10:00:00",
            "participant_count": 5,
        },
    }

    await builder.handle_event(event_data)

    meeting = await projection_repo.get_meeting(meeting_id)
    assert meeting is not None
    assert meeting.id == meeting_id
    assert meeting.title == "Sprint Planning"
    assert meeting.date == "2026-01-19T10:00:00"
    assert meeting.participant_count == 5


@pytest.mark.asyncio
async def test_handle_action_item_extracted_event(
    builder: ProjectionBuilder, projection_repo: ProjectionRepository
):
    """handle_event should create RAID item projection from ActionItemExtracted."""
    action_id = str(uuid4())
    meeting_id = str(uuid4())
    event_data = {
        "event_type": "ActionItemExtracted",
        "aggregate_id": action_id,
        "data": {
            "action_item_id": action_id,
            "meeting_id": meeting_id,
            "description": "Complete the API documentation",
            "assignee_name": "John Doe",
            "due_date": "2026-01-25",
            "confidence": 0.85,
        },
    }

    await builder.handle_event(event_data)

    item = await projection_repo.get_raid_item(action_id)
    assert item is not None
    assert item.id == action_id
    assert item.meeting_id == meeting_id
    assert item.item_type == "action"
    assert item.description == "Complete the API documentation"
    assert item.owner == "John Doe"
    assert item.due_date == "2026-01-25"
    assert item.confidence == 0.85
    assert item.status == "pending"


@pytest.mark.asyncio
async def test_handle_decision_extracted_event(
    builder: ProjectionBuilder, projection_repo: ProjectionRepository
):
    """handle_event should create RAID item projection from DecisionExtracted."""
    decision_id = str(uuid4())
    meeting_id = str(uuid4())
    event_data = {
        "event_type": "DecisionExtracted",
        "aggregate_id": decision_id,
        "data": {
            "decision_id": decision_id,
            "meeting_id": meeting_id,
            "description": "Use REST API for the new service",
            "confidence": 0.9,
        },
    }

    await builder.handle_event(event_data)

    item = await projection_repo.get_raid_item(decision_id)
    assert item is not None
    assert item.id == decision_id
    assert item.item_type == "decision"
    assert item.description == "Use REST API for the new service"
    assert item.confidence == 0.9


@pytest.mark.asyncio
async def test_handle_risk_extracted_event(
    builder: ProjectionBuilder, projection_repo: ProjectionRepository
):
    """handle_event should create RAID item projection from RiskExtracted."""
    risk_id = str(uuid4())
    meeting_id = str(uuid4())
    event_data = {
        "event_type": "RiskExtracted",
        "aggregate_id": risk_id,
        "data": {
            "risk_id": risk_id,
            "meeting_id": meeting_id,
            "description": "Database migration might cause downtime",
            "severity": "high",
            "confidence": 0.75,
        },
    }

    await builder.handle_event(event_data)

    item = await projection_repo.get_raid_item(risk_id)
    assert item is not None
    assert item.id == risk_id
    assert item.item_type == "risk"
    assert item.description == "Database migration might cause downtime"
    assert item.confidence == 0.75


@pytest.mark.asyncio
async def test_handle_issue_extracted_event(
    builder: ProjectionBuilder, projection_repo: ProjectionRepository
):
    """handle_event should create RAID item projection from IssueExtracted."""
    issue_id = str(uuid4())
    meeting_id = str(uuid4())
    event_data = {
        "event_type": "IssueExtracted",
        "aggregate_id": issue_id,
        "data": {
            "issue_id": issue_id,
            "meeting_id": meeting_id,
            "description": "CI pipeline is failing intermittently",
            "priority": "high",
            "confidence": 0.8,
        },
    }

    await builder.handle_event(event_data)

    item = await projection_repo.get_raid_item(issue_id)
    assert item is not None
    assert item.id == issue_id
    assert item.item_type == "issue"
    assert item.description == "CI pipeline is failing intermittently"
    assert item.confidence == 0.8


@pytest.mark.asyncio
async def test_handle_unknown_event_type(builder: ProjectionBuilder):
    """handle_event should ignore unknown event types without error."""
    event_data = {
        "event_type": "SomeUnknownEvent",
        "aggregate_id": str(uuid4()),
        "data": {"foo": "bar"},
    }

    # Should not raise
    await builder.handle_event(event_data)


@pytest.mark.asyncio
async def test_rebuild_all_processes_events(
    builder: ProjectionBuilder,
    event_store: EventStore,
    projection_repo: ProjectionRepository,
):
    """rebuild_all should process all events and return stats."""
    # Add events to the store manually
    from src.events.types import (
        ActionItemExtracted,
        DecisionExtracted,
        MeetingCreated,
    )

    meeting_id = uuid4()

    # Create a meeting event
    meeting_event = MeetingCreated(
        aggregate_id=meeting_id,
        title="Test Meeting",
        meeting_date="2026-01-19T10:00:00",
        participant_count=3,
    )
    await event_store.append(meeting_event)

    # Create action item event
    action_id = uuid4()
    action_event = ActionItemExtracted(
        aggregate_id=action_id,
        meeting_id=meeting_id,
        action_item_id=action_id,
        description="Test action",
        confidence=0.9,
    )
    await event_store.append(action_event)

    # Create decision event
    decision_id = uuid4()
    decision_event = DecisionExtracted(
        aggregate_id=decision_id,
        meeting_id=meeting_id,
        decision_id=decision_id,
        description="Test decision",
        confidence=0.85,
    )
    await event_store.append(decision_event)

    # Rebuild projections
    stats = await builder.rebuild_all()

    assert stats["meetings"] == 1
    assert stats["raid_items"] == 2
    assert stats["transcripts"] == 0

    # Verify projections exist
    meeting = await projection_repo.get_meeting(str(meeting_id))
    assert meeting is not None
    assert meeting.title == "Test Meeting"

    action = await projection_repo.get_raid_item(str(action_id))
    assert action is not None
    assert action.description == "Test action"


@pytest.mark.asyncio
async def test_rebuild_all_clears_existing_projections(
    builder: ProjectionBuilder,
    projection_repo: ProjectionRepository,
):
    """rebuild_all should clear existing projections before rebuilding."""
    from src.search.schemas import MeetingProjection

    # Add existing projection
    await projection_repo.upsert_meeting(
        MeetingProjection(id="old-meeting", title="Old Meeting")
    )

    # Rebuild (with empty event store)
    stats = await builder.rebuild_all()

    # Old projection should be gone
    meeting = await projection_repo.get_meeting("old-meeting")
    assert meeting is None
    assert stats["meetings"] == 0


@pytest.mark.asyncio
async def test_handle_meeting_created_missing_aggregate_id(
    builder: ProjectionBuilder, projection_repo: ProjectionRepository
):
    """handle_event should handle missing aggregate_id gracefully."""
    event_data = {
        "event_type": "MeetingCreated",
        # No aggregate_id
        "data": {
            "title": "Sprint Planning",
        },
    }

    # Should not raise
    await builder.handle_event(event_data)

    # Should not have created a projection with None id
    result = await projection_repo._db.execute(
        "SELECT COUNT(*) FROM meetings_projection"
    )
    assert result.rows[0][0] == 0
