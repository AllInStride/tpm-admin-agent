"""Append-only event store using Turso/libSQL.

The event store persists all domain events for:
- Audit trail
- Event replay
- Building projections
- Debugging
"""

import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID

from src.db.turso import TursoClient
from src.events.base import Event

logger = logging.getLogger(__name__)


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails."""


class EventStore:
    """Append-only event store using Turso/libSQL.

    Features:
    - Append-only (never update/delete)
    - Optimistic concurrency control
    - Event retrieval by aggregate
    - Event replay support
    """

    def __init__(self, client: TursoClient):
        """Initialize event store.

        Args:
            client: Database client for persistence
        """
        self.client = client

    async def init_schema(self) -> None:
        """Create the events table if it doesn't exist."""
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                aggregate_id TEXT,
                aggregate_type TEXT,
                event_data TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                version INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.client.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_aggregate
            ON events(aggregate_type, aggregate_id, version)
        """)
        await self.client.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(event_type)
        """)
        await self.client.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON events(timestamp)
        """)
        logger.info("Event store schema initialized")

    async def append(
        self,
        event: Event,
        expected_version: int | None = None,
    ) -> None:
        """Append an event to the store.

        Args:
            event: The event to store
            expected_version: For optimistic concurrency (optional)

        Raises:
            ConcurrencyError: If expected_version doesn't match
        """
        store_dict = event.to_store_dict()
        event_data = json.dumps(store_dict["data"], default=str)

        # Handle optimistic concurrency if aggregate_id is set
        version = None
        if event.aggregate_id and expected_version is not None:
            result = await self.client.execute(
                "SELECT MAX(version) FROM events WHERE aggregate_id = ?",
                [str(event.aggregate_id)],
            )
            current_version = result.rows[0][0] if result.rows[0][0] else 0
            if current_version != expected_version:
                msg = f"Expected version {expected_version}, got {current_version}"
                raise ConcurrencyError(msg)
            version = current_version + 1

        await self.client.execute(
            """INSERT INTO events
               (event_id, event_type, aggregate_id, aggregate_type,
                event_data, timestamp, version)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                str(event.event_id),
                event.event_type,
                str(event.aggregate_id) if event.aggregate_id else None,
                event.aggregate_type,
                event_data,
                event.timestamp.isoformat(),
                version,
            ],
        )
        logger.debug(f"Stored event {event.event_type} ({event.event_id})")

    async def get_events_for_aggregate(
        self,
        aggregate_id: UUID,
        from_version: int = 0,
    ) -> AsyncIterator[dict]:
        """Retrieve events for an aggregate.

        Args:
            aggregate_id: The aggregate's ID
            from_version: Start from this version (exclusive)

        Yields:
            Event dictionaries
        """
        result = await self.client.execute(
            """SELECT event_type, event_data, version, timestamp
               FROM events
               WHERE aggregate_id = ? AND (version > ? OR version IS NULL)
               ORDER BY id ASC""",
            [str(aggregate_id), from_version],
        )
        for row in result.rows:
            yield {
                "event_type": row[0],
                "data": json.loads(row[1]),
                "version": row[2],
                "timestamp": row[3],
            }

    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> AsyncIterator[dict]:
        """Retrieve events by type.

        Args:
            event_type: Event type name (class name)
            limit: Maximum events to return
            offset: Number of events to skip

        Yields:
            Event dictionaries
        """
        result = await self.client.execute(
            """SELECT event_id, event_type, aggregate_id, event_data, timestamp
               FROM events
               WHERE event_type = ?
               ORDER BY id DESC
               LIMIT ? OFFSET ?""",
            [event_type, limit, offset],
        )
        for row in result.rows:
            yield {
                "event_id": row[0],
                "event_type": row[1],
                "aggregate_id": row[2],
                "data": json.loads(row[3]),
                "timestamp": row[4],
            }

    async def get_all_events(
        self,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> AsyncIterator[dict]:
        """Retrieve all events, optionally since a timestamp.

        Args:
            since: Only return events after this timestamp
            limit: Maximum events to return

        Yields:
            Event dictionaries
        """
        if since:
            result = await self.client.execute(
                """SELECT event_id, event_type, aggregate_id, event_data, timestamp
                   FROM events
                   WHERE timestamp > ?
                   ORDER BY id ASC
                   LIMIT ?""",
                [since.isoformat(), limit],
            )
        else:
            result = await self.client.execute(
                """SELECT event_id, event_type, aggregate_id, event_data, timestamp
                   FROM events
                   ORDER BY id ASC
                   LIMIT ?""",
                [limit],
            )
        for row in result.rows:
            yield {
                "event_id": row[0],
                "event_type": row[1],
                "aggregate_id": row[2],
                "data": json.loads(row[3]),
                "timestamp": row[4],
            }

    async def count_events(self, event_type: str | None = None) -> int:
        """Count events, optionally by type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            Number of events
        """
        if event_type:
            result = await self.client.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = ?",
                [event_type],
            )
        else:
            result = await self.client.execute("SELECT COUNT(*) FROM events")
        return result.rows[0][0]
