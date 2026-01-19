"""Integration tests for projection pipeline.

Tests that events automatically update projections when
the projection builder is wired to the event bus.
"""

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.db.turso import TursoClient
from src.events.bus import EventBus
from src.events.store import EventStore
from src.events.types import (
    ActionItemExtracted,
    DecisionExtracted,
    MeetingCreated,
    RiskExtracted,
)
from src.main import app
from src.repositories.projection_repo import ProjectionRepository
from src.search.projections import ProjectionBuilder


@pytest.fixture
async def integration_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    """Create async test client with projection pipeline wired up."""
    # Set up test database
    db_path = tmp_path / "test_projection_integration.db"
    db = TursoClient(url=f"file:{db_path}")
    await db.connect()

    # Initialize event store
    event_store = EventStore(db)
    await event_store.init_schema()

    # Initialize event bus with store
    event_bus = EventBus(store=event_store)

    # Initialize projection repository
    projection_repo = ProjectionRepository(db)
    await projection_repo.initialize()

    # Initialize projection builder and wire to event bus
    projection_builder = ProjectionBuilder(event_store, projection_repo)

    # Subscribe to all event types
    from src.events.types import (
        IssueExtracted,
        TranscriptParsed,
    )

    event_types = [
        MeetingCreated,
        TranscriptParsed,
        ActionItemExtracted,
        DecisionExtracted,
        RiskExtracted,
        IssueExtracted,
    ]

    for event_type in event_types:
        event_bus.subscribe(event_type, projection_builder.handle_event_object)

    # Set up app state
    app.state.db = db
    app.state.event_store = event_store
    app.state.event_bus = event_bus
    app.state.projection_repo = projection_repo
    app.state.projection_builder = projection_builder

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    await db.close()
    del app.state.db
    del app.state.event_store
    del app.state.event_bus
    del app.state.projection_repo
    del app.state.projection_builder


@pytest.mark.asyncio
async def test_event_bus_updates_projections(
    integration_client: AsyncClient,
):
    """Publishing events through event bus should update projections."""
    event_bus = app.state.event_bus
    projection_repo = app.state.projection_repo

    # Create and publish a MeetingCreated event
    meeting_id = uuid4()
    meeting_event = MeetingCreated(
        aggregate_id=meeting_id,
        title="Integration Test Meeting",
        meeting_date="2026-01-19T10:00:00",
        participant_count=3,
    )
    await event_bus.publish(meeting_event)

    # Verify meeting projection was created
    meeting = await projection_repo.get_meeting(str(meeting_id))
    assert meeting is not None
    assert meeting.title == "Integration Test Meeting"


@pytest.mark.asyncio
async def test_action_item_event_creates_projection(
    integration_client: AsyncClient,
):
    """ActionItemExtracted event should create RAID item projection."""
    event_bus = app.state.event_bus
    projection_repo = app.state.projection_repo

    meeting_id = uuid4()
    action_id = uuid4()

    action_event = ActionItemExtracted(
        aggregate_id=action_id,
        meeting_id=meeting_id,
        action_item_id=action_id,
        description="Complete integration tests",
        assignee_name="Alice",
        confidence=0.9,
    )
    await event_bus.publish(action_event)

    # Verify RAID item projection was created
    item = await projection_repo.get_raid_item(str(action_id))
    assert item is not None
    assert item.item_type == "action"
    assert item.description == "Complete integration tests"
    assert item.owner == "Alice"


@pytest.mark.asyncio
async def test_decision_event_creates_projection(
    integration_client: AsyncClient,
):
    """DecisionExtracted event should create RAID item projection."""
    event_bus = app.state.event_bus
    projection_repo = app.state.projection_repo

    meeting_id = uuid4()
    decision_id = uuid4()

    decision_event = DecisionExtracted(
        aggregate_id=decision_id,
        meeting_id=meeting_id,
        decision_id=decision_id,
        description="Use PostgreSQL for production",
        confidence=0.95,
    )
    await event_bus.publish(decision_event)

    # Verify RAID item projection was created
    item = await projection_repo.get_raid_item(str(decision_id))
    assert item is not None
    assert item.item_type == "decision"
    assert item.description == "Use PostgreSQL for production"


@pytest.mark.asyncio
async def test_risk_event_creates_projection(
    integration_client: AsyncClient,
):
    """RiskExtracted event should create RAID item projection."""
    event_bus = app.state.event_bus
    projection_repo = app.state.projection_repo

    meeting_id = uuid4()
    risk_id = uuid4()

    risk_event = RiskExtracted(
        aggregate_id=risk_id,
        meeting_id=meeting_id,
        risk_id=risk_id,
        description="Migration may cause downtime",
        severity="high",
        confidence=0.8,
    )
    await event_bus.publish(risk_event)

    # Verify RAID item projection was created
    item = await projection_repo.get_raid_item(str(risk_id))
    assert item is not None
    assert item.item_type == "risk"
    assert item.description == "Migration may cause downtime"


@pytest.mark.asyncio
async def test_fts_search_after_event_publish(
    integration_client: AsyncClient,
):
    """FTS5 search should find items after event publication."""
    event_bus = app.state.event_bus
    projection_repo = app.state.projection_repo

    meeting_id = uuid4()
    action_id = uuid4()

    action_event = ActionItemExtracted(
        aggregate_id=action_id,
        meeting_id=meeting_id,
        action_item_id=action_id,
        description="Implement database caching layer",
        assignee_name="Bob",
        confidence=0.88,
    )
    await event_bus.publish(action_event)

    # Search using FTS
    results = await projection_repo.search_raid_items("database caching")
    assert len(results) == 1
    assert results[0].id == str(action_id)
    assert "database caching" in results[0].description.lower()


@pytest.mark.asyncio
async def test_multiple_events_create_multiple_projections(
    integration_client: AsyncClient,
):
    """Publishing multiple events should create multiple projections."""
    event_bus = app.state.event_bus
    projection_repo = app.state.projection_repo

    meeting_id = uuid4()

    # Create meeting
    meeting_event = MeetingCreated(
        aggregate_id=meeting_id,
        title="Multi-Event Test",
        meeting_date="2026-01-20T09:00:00",
        participant_count=5,
    )
    await event_bus.publish(meeting_event)

    # Create multiple RAID items
    action_ids = []
    for i in range(3):
        action_id = uuid4()
        action_ids.append(action_id)
        action_event = ActionItemExtracted(
            aggregate_id=action_id,
            meeting_id=meeting_id,
            action_item_id=action_id,
            description=f"Task {i + 1}: Complete feature {i + 1}",
            confidence=0.9,
        )
        await event_bus.publish(action_event)

    # Verify all projections were created
    meeting = await projection_repo.get_meeting(str(meeting_id))
    assert meeting is not None

    for action_id in action_ids:
        item = await projection_repo.get_raid_item(str(action_id))
        assert item is not None
        assert item.item_type == "action"
