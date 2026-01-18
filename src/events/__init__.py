"""Event infrastructure for TPM Admin Agent.

Provides:
- Event: Base class for all domain events
- EventBus: In-process pub/sub for event routing
- EventStore: Append-only event persistence
"""

from src.events.base import Event
from src.events.bus import EventBus
from src.events.store import ConcurrencyError, EventStore
from src.events.types import (
    ActionItemExtracted,
    DecisionExtracted,
    IssueExtracted,
    MeetingCreated,
    MeetingProcessed,
    RiskExtracted,
    TranscriptParsed,
)

__all__ = [
    # Base
    "Event",
    # Infrastructure
    "EventBus",
    "EventStore",
    "ConcurrencyError",
    # Event types
    "MeetingCreated",
    "TranscriptParsed",
    "MeetingProcessed",
    "ActionItemExtracted",
    "DecisionExtracted",
    "RiskExtracted",
    "IssueExtracted",
]
