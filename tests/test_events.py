"""Tests for event infrastructure."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.db.turso import TursoClient
from src.events import (
    ActionItemExtracted,
    ConcurrencyError,
    Event,
    EventBus,
    EventStore,
    MeetingCreated,
    MeetingProcessed,
)


class TestEvent:
    """Tests for base Event class."""

    def test_creates_with_defaults(self) -> None:
        """Event generates event_id and timestamp."""

        class TestEvent(Event):
            message: str

        e = TestEvent(message="test")
        assert e.event_id is not None
        assert e.timestamp is not None
        assert e.event_type == "TestEvent"

    def test_is_immutable(self) -> None:
        """Events are frozen (immutable)."""

        class TestEvent(Event):
            message: str

        e = TestEvent(message="test")
        with pytest.raises(Exception):  # ValidationError for frozen model
            e.message = "changed"  # type: ignore[misc]

    def test_to_store_dict(self) -> None:
        """Event converts to storage dictionary."""
        aggregate_id = uuid4()
        e = MeetingCreated(
            aggregate_id=aggregate_id,
            title="Test Meeting",
            meeting_date=datetime.now(UTC),
            participant_count=5,
        )
        d = e.to_store_dict()
        assert d["event_type"] == "MeetingCreated"
        assert d["aggregate_id"] == str(aggregate_id)
        assert "title" in d["data"]


class TestEventTypes:
    """Tests for typed event definitions."""

    def test_meeting_created(self) -> None:
        """MeetingCreated event has required fields."""
        e = MeetingCreated(
            aggregate_id=uuid4(),
            title="Weekly Standup",
            meeting_date=datetime.now(UTC),
        )
        assert e.aggregate_type == "Meeting"
        assert e.title == "Weekly Standup"

    def test_action_item_extracted(self) -> None:
        """ActionItemExtracted event has required fields."""
        meeting_id = uuid4()
        action_id = uuid4()
        e = ActionItemExtracted(
            aggregate_id=action_id,
            meeting_id=meeting_id,
            action_item_id=action_id,
            description="Review the PR",
            assignee_name="Alice",
            confidence=0.95,
        )
        assert e.meeting_id == meeting_id
        assert e.confidence == 0.95

    def test_meeting_processed(self) -> None:
        """MeetingProcessed event captures counts."""
        e = MeetingProcessed(
            aggregate_id=uuid4(),
            action_item_count=3,
            decision_count=2,
            risk_count=1,
            issue_count=0,
            processing_time_ms=1500,
        )
        assert e.action_item_count == 3
        assert e.processing_time_ms == 1500


class TestEventBus:
    """Tests for EventBus."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self) -> None:
        """Event bus delivers events to subscribers."""
        bus = EventBus()
        received: list[MeetingCreated] = []

        async def handler(event: MeetingCreated) -> None:
            received.append(event)

        bus.subscribe(MeetingCreated, handler)

        event = MeetingCreated(
            aggregate_id=uuid4(),
            title="Test",
            meeting_date=datetime.now(UTC),
        )
        await bus.publish(event)

        assert len(received) == 1
        assert received[0].title == "Test"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self) -> None:
        """Multiple subscribers all receive events."""
        bus = EventBus()
        results: dict[str, list[MeetingCreated]] = {"handler1": [], "handler2": []}

        async def handler1(event: MeetingCreated) -> None:
            results["handler1"].append(event)

        async def handler2(event: MeetingCreated) -> None:
            results["handler2"].append(event)

        bus.subscribe(MeetingCreated, handler1)
        bus.subscribe(MeetingCreated, handler2)

        await bus.publish(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Test",
                meeting_date=datetime.now(UTC),
            )
        )

        assert len(results["handler1"]) == 1
        assert len(results["handler2"]) == 1

    @pytest.mark.asyncio
    async def test_sync_handler(self) -> None:
        """Sync handlers work via thread pool."""
        bus = EventBus()
        received: list[MeetingCreated] = []

        def sync_handler(event: MeetingCreated) -> None:
            received.append(event)

        bus.subscribe(MeetingCreated, sync_handler)

        await bus.publish(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Test",
                meeting_date=datetime.now(UTC),
            )
        )

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_type_isolation(self) -> None:
        """Handlers only receive events of subscribed type."""
        bus = EventBus()
        meeting_events: list[MeetingCreated] = []
        action_events: list[ActionItemExtracted] = []

        async def meeting_handler(event: MeetingCreated) -> None:
            meeting_events.append(event)

        async def action_handler(event: ActionItemExtracted) -> None:
            action_events.append(event)

        bus.subscribe(MeetingCreated, meeting_handler)
        bus.subscribe(ActionItemExtracted, action_handler)

        await bus.publish(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Test",
                meeting_date=datetime.now(UTC),
            )
        )

        assert len(meeting_events) == 1
        assert len(action_events) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe(self) -> None:
        """Unsubscribed handlers don't receive events."""
        bus = EventBus()
        received: list[MeetingCreated] = []

        async def handler(event: MeetingCreated) -> None:
            received.append(event)

        bus.subscribe(MeetingCreated, handler)
        bus.unsubscribe(MeetingCreated, handler)

        await bus.publish(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Test",
                meeting_date=datetime.now(UTC),
            )
        )

        assert len(received) == 0

    def test_subscriber_count(self) -> None:
        """Can count subscribers for event type."""
        bus = EventBus()

        async def h1(e: MeetingCreated) -> None:
            pass

        async def h2(e: MeetingCreated) -> None:
            pass

        assert bus.subscriber_count(MeetingCreated) == 0
        bus.subscribe(MeetingCreated, h1)
        assert bus.subscriber_count(MeetingCreated) == 1
        bus.subscribe(MeetingCreated, h2)
        assert bus.subscriber_count(MeetingCreated) == 2


class TestEventStore:
    """Tests for EventStore with SQLite."""

    @pytest.fixture
    async def store(self, tmp_path: Path) -> EventStore:
        """Create event store with temp file database."""
        db_path = tmp_path / "test_events.db"
        client = TursoClient(url=f"file:{db_path}")
        await client.connect()
        store = EventStore(client)
        await store.init_schema()
        return store

    @pytest.mark.asyncio
    async def test_append_event(self, store: EventStore) -> None:
        """Can append an event to the store."""
        event = MeetingCreated(
            aggregate_id=uuid4(),
            title="Test Meeting",
            meeting_date=datetime.now(UTC),
        )
        await store.append(event)
        count = await store.count_events()
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_events_for_aggregate(self, store: EventStore) -> None:
        """Can retrieve events for an aggregate."""
        aggregate_id = uuid4()

        # Append multiple events for same aggregate
        await store.append(
            MeetingCreated(
                aggregate_id=aggregate_id,
                title="Meeting 1",
                meeting_date=datetime.now(UTC),
            )
        )
        await store.append(
            MeetingProcessed(
                aggregate_id=aggregate_id,
                action_item_count=2,
            )
        )

        # Append event for different aggregate
        await store.append(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Meeting 2",
                meeting_date=datetime.now(UTC),
            )
        )

        events = [e async for e in store.get_events_for_aggregate(aggregate_id)]
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_get_events_by_type(self, store: EventStore) -> None:
        """Can retrieve events by type."""
        await store.append(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Meeting 1",
                meeting_date=datetime.now(UTC),
            )
        )
        await store.append(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Meeting 2",
                meeting_date=datetime.now(UTC),
            )
        )
        await store.append(MeetingProcessed(aggregate_id=uuid4(), action_item_count=1))

        events = [e async for e in store.get_events_by_type("MeetingCreated")]
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_count_events(self, store: EventStore) -> None:
        """Can count events with optional type filter."""
        await store.append(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Test",
                meeting_date=datetime.now(UTC),
            )
        )
        await store.append(MeetingProcessed(aggregate_id=uuid4(), action_item_count=1))

        assert await store.count_events() == 2
        assert await store.count_events("MeetingCreated") == 1
        assert await store.count_events("MeetingProcessed") == 1

    @pytest.mark.asyncio
    async def test_concurrency_control(self, store: EventStore) -> None:
        """Optimistic concurrency control works."""
        aggregate_id = uuid4()

        # First event with version check
        await store.append(
            MeetingCreated(
                aggregate_id=aggregate_id,
                title="Test",
                meeting_date=datetime.now(UTC),
            ),
            expected_version=0,
        )

        # Second event expecting version 1
        await store.append(
            MeetingProcessed(
                aggregate_id=aggregate_id,
                action_item_count=1,
            ),
            expected_version=1,
        )

        # Third event with wrong version should fail
        with pytest.raises(ConcurrencyError):
            await store.append(
                MeetingProcessed(
                    aggregate_id=aggregate_id,
                    action_item_count=2,
                ),
                expected_version=1,  # Should be 2
            )


class TestEventBusWithStore:
    """Tests for EventBus with EventStore integration."""

    @pytest.fixture
    async def bus_with_store(self, tmp_path: Path) -> EventBus:
        """Create event bus with temp file store."""
        db_path = tmp_path / "test_bus_store.db"
        client = TursoClient(url=f"file:{db_path}")
        await client.connect()
        store = EventStore(client)
        await store.init_schema()
        return EventBus(store=store)

    @pytest.mark.asyncio
    async def test_publish_and_store(self, bus_with_store: EventBus) -> None:
        """publish_and_store persists event."""
        received: list[MeetingCreated] = []

        async def handler(event: MeetingCreated) -> None:
            received.append(event)

        bus_with_store.subscribe(MeetingCreated, handler)

        await bus_with_store.publish_and_store(
            MeetingCreated(
                aggregate_id=uuid4(),
                title="Test",
                meeting_date=datetime.now(UTC),
            )
        )

        # Handler received event
        assert len(received) == 1

        # Event was stored
        assert bus_with_store._store is not None
        count = await bus_with_store._store.count_events()
        assert count == 1
