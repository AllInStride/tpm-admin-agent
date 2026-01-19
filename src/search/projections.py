"""Projection builder for materializing events into read models.

ProjectionBuilder processes domain events and updates projection tables
to maintain queryable state for cross-meeting intelligence features.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.events.store import EventStore
from src.repositories.projection_repo import ProjectionRepository
from src.search.schemas import (
    MeetingProjection,
    RaidItemProjection,
)

if TYPE_CHECKING:
    from src.events.base import Event

logger = logging.getLogger(__name__)


def _to_string(value: Any) -> str | None:
    """Convert a value to string, handling datetime objects.

    Args:
        value: Value to convert (may be datetime, str, or None)

    Returns:
        String representation or None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


# Event type constants
EVENT_MEETING_CREATED = "MeetingCreated"
EVENT_TRANSCRIPT_PARSED = "TranscriptParsed"
EVENT_ACTION_ITEM_EXTRACTED = "ActionItemExtracted"
EVENT_DECISION_EXTRACTED = "DecisionExtracted"
EVENT_RISK_EXTRACTED = "RiskExtracted"
EVENT_ISSUE_EXTRACTED = "IssueExtracted"


class ProjectionBuilder:
    """Materializes domain events into searchable read projections.

    Processes events from the event store and updates projection tables
    so they reflect current state optimized for queries.
    """

    def __init__(
        self,
        event_store: EventStore,
        projection_repo: ProjectionRepository,
    ):
        """Initialize projection builder.

        Args:
            event_store: Event store for replay operations
            projection_repo: Repository for projection table operations
        """
        self._event_store = event_store
        self._projection_repo = projection_repo

    async def handle_event(self, event_data: dict) -> None:
        """Route event to appropriate handler based on event type.

        Args:
            event_data: Event dictionary with event_type and data fields
        """
        event_type = event_data.get("event_type")
        data = event_data.get("data", {})

        handler_map = {
            EVENT_MEETING_CREATED: self._handle_meeting_created,
            EVENT_TRANSCRIPT_PARSED: self._handle_transcript_parsed,
            EVENT_ACTION_ITEM_EXTRACTED: self._handle_action_item,
            EVENT_DECISION_EXTRACTED: self._handle_decision,
            EVENT_RISK_EXTRACTED: self._handle_risk,
            EVENT_ISSUE_EXTRACTED: self._handle_issue,
        }

        handler = handler_map.get(event_type)
        if handler:
            try:
                await handler(data, event_data)
            except Exception as e:
                logger.error(f"Error handling {event_type}: {e}")
                raise
        else:
            logger.debug(f"No projection handler for event type: {event_type}")

    async def _handle_meeting_created(self, data: dict, event_data: dict) -> None:
        """Handle MeetingCreated event.

        Creates or updates meeting projection.
        """
        # aggregate_id comes from the event wrapper, not data
        meeting_id = event_data.get("aggregate_id")
        if not meeting_id:
            logger.warning("MeetingCreated event missing aggregate_id")
            return

        projection = MeetingProjection(
            id=str(meeting_id),
            title=data.get("title", "Untitled Meeting"),
            date=_to_string(data.get("meeting_date")),
            participant_count=data.get("participant_count", 0),
        )
        await self._projection_repo.upsert_meeting(projection)
        logger.debug(f"Projected meeting: {meeting_id}")

    async def _handle_transcript_parsed(self, data: dict, event_data: dict) -> None:
        """Handle TranscriptParsed event.

        The transcript content itself is in the data. Parse utterances
        and insert into transcripts_projection.

        Note: TranscriptParsed typically contains metadata (utterance_count,
        speaker_count, duration) but not the actual utterances. The raw
        transcript data would need to be fetched separately or included
        in a different event. For now, we skip transcript projection
        as the utterance data isn't directly in this event.
        """
        # TranscriptParsed contains metadata, not raw transcript content
        # Actual transcript utterances would come from a separate event
        # or be processed at upload time
        aggregate_id = event_data.get("aggregate_id")
        logger.debug(
            f"TranscriptParsed event for meeting {aggregate_id}: "
            f"{data.get('utterance_count', 0)} utterances"
        )

    async def _handle_action_item(self, data: dict, event_data: dict) -> None:
        """Handle ActionItemExtracted event.

        Creates RAID item projection with type='action'.
        """
        projection = RaidItemProjection(
            id=str(data.get("action_item_id")),
            meeting_id=str(data.get("meeting_id")),
            item_type="action",
            description=data.get("description", ""),
            owner=data.get("assignee_name"),
            due_date=_to_string(data.get("due_date")),
            status="pending",
            confidence=data.get("confidence", 1.0),
        )
        await self._projection_repo.upsert_raid_item(projection)
        logger.debug(f"Projected action item: {projection.id}")

    async def _handle_decision(self, data: dict, event_data: dict) -> None:
        """Handle DecisionExtracted event.

        Creates RAID item projection with type='decision'.
        """
        projection = RaidItemProjection(
            id=str(data.get("decision_id")),
            meeting_id=str(data.get("meeting_id")),
            item_type="decision",
            description=data.get("description", ""),
            owner=None,  # Decisions typically don't have owners
            due_date=None,  # Decisions don't have due dates
            status="pending",
            confidence=data.get("confidence", 1.0),
        )
        await self._projection_repo.upsert_raid_item(projection)
        logger.debug(f"Projected decision: {projection.id}")

    async def _handle_risk(self, data: dict, event_data: dict) -> None:
        """Handle RiskExtracted event.

        Creates RAID item projection with type='risk'.
        """
        projection = RaidItemProjection(
            id=str(data.get("risk_id")),
            meeting_id=str(data.get("meeting_id")),
            item_type="risk",
            description=data.get("description", ""),
            owner=None,  # Risks may have owners, but not in current schema
            due_date=None,
            status="pending",
            confidence=data.get("confidence", 1.0),
        )
        await self._projection_repo.upsert_raid_item(projection)
        logger.debug(f"Projected risk: {projection.id}")

    async def _handle_issue(self, data: dict, event_data: dict) -> None:
        """Handle IssueExtracted event.

        Creates RAID item projection with type='issue'.
        """
        projection = RaidItemProjection(
            id=str(data.get("issue_id")),
            meeting_id=str(data.get("meeting_id")),
            item_type="issue",
            description=data.get("description", ""),
            owner=None,  # Issues may have owners, but not in current schema
            due_date=None,
            status="pending",
            confidence=data.get("confidence", 1.0),
        )
        await self._projection_repo.upsert_raid_item(projection)
        logger.debug(f"Projected issue: {projection.id}")

    async def rebuild_all(self) -> dict:
        """Rebuild all projections from the event store.

        Clears existing projections and replays all events to rebuild
        current state. Use for recovery or migration scenarios.

        Returns:
            Statistics dict with counts of processed items:
            {"meetings": N, "raid_items": N, "transcripts": N}
        """
        logger.info("Starting projection rebuild from event store")

        # Clear existing projections
        await self._projection_repo.clear_all_projections()

        # Track statistics
        stats = {"meetings": 0, "raid_items": 0, "transcripts": 0}

        # Replay all events
        async for event in self._event_store.get_all_events(limit=100000):
            event_type = event.get("event_type")

            # Process event
            await self.handle_event(event)

            # Update stats based on event type
            if event_type == EVENT_MEETING_CREATED:
                stats["meetings"] += 1
            elif event_type in (
                EVENT_ACTION_ITEM_EXTRACTED,
                EVENT_DECISION_EXTRACTED,
                EVENT_RISK_EXTRACTED,
                EVENT_ISSUE_EXTRACTED,
            ):
                stats["raid_items"] += 1
            elif event_type == EVENT_TRANSCRIPT_PARSED:
                stats["transcripts"] += 1

        # Rebuild FTS indexes after bulk load
        await self._projection_repo.rebuild_fts_indexes()

        logger.info(f"Projection rebuild complete: {stats}")
        return stats

    async def handle_event_object(self, event: "Event") -> None:
        """Handle an Event object directly (for event bus integration).

        Converts Event to dict format and processes it.

        Args:
            event: Event object from event bus
        """
        event_dict = event.to_store_dict()
        # Flatten structure for handle_event
        event_data = {
            "event_type": event_dict.get("event_type"),
            "aggregate_id": event_dict.get("aggregate_id"),
            "data": event_dict.get("data", {}),
        }
        await self.handle_event(event_data)
