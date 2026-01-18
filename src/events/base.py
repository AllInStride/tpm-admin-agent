"""Base Event class for all domain events."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    """Base class for all domain events.

    Events are immutable records of things that happened.
    They are the source of truth in an event-sourced system.

    Attributes:
        event_id: Unique identifier for this event instance
        timestamp: When the event occurred
        aggregate_id: ID of the entity this event relates to (optional)
        aggregate_type: Type of the entity (e.g., "Meeting", "ActionItem")
        metadata: Additional context about the event
    """

    model_config = ConfigDict(
        frozen=True,  # Events are immutable
        str_strip_whitespace=True,
    )

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique event identifier",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the event occurred",
    )
    aggregate_id: UUID | None = Field(
        default=None,
        description="ID of the related entity",
    )
    aggregate_type: str | None = Field(
        default=None,
        description="Type of the related entity",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event context",
    )

    @property
    def event_type(self) -> str:
        """Return the event type name (class name)."""
        return self.__class__.__name__

    def to_store_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for storage.

        Returns a dict suitable for JSON serialization and database storage.
        """
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_type": self.aggregate_type,
            "data": self.model_dump(
                exclude={"event_id", "timestamp", "aggregate_id", "aggregate_type"}
            ),
        }
