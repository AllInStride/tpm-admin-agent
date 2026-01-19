"""Projection schemas for read models.

These schemas represent materialized views derived from events,
optimized for query patterns rather than write patterns.
"""

from typing import Literal

from pydantic import BaseModel, Field


class MeetingProjection(BaseModel):
    """Read projection for meetings.

    Materialized from MeetingCreated events.
    """

    id: str = Field(description="Meeting UUID")
    title: str = Field(description="Meeting title")
    date: str | None = Field(default=None, description="Meeting date (ISO format)")
    participant_count: int = Field(default=0, description="Number of participants")
    created_at: str | None = Field(default=None, description="When projection created")


class RaidItemProjection(BaseModel):
    """Read projection for RAID items (Risks, Actions, Issues, Decisions).

    Materialized from ActionItemExtracted, DecisionExtracted,
    RiskExtracted, and IssueExtracted events.
    """

    id: str = Field(description="Item UUID")
    meeting_id: str = Field(description="Source meeting UUID")
    item_type: Literal["action", "decision", "risk", "issue"] = Field(
        description="RAID item type"
    )
    description: str = Field(description="Item description")
    owner: str | None = Field(default=None, description="Assigned owner")
    due_date: str | None = Field(default=None, description="Due date (ISO format)")
    status: Literal["pending", "completed", "cancelled", "closed", "resolved"] = Field(
        default="pending", description="Item status"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )
    created_at: str | None = Field(default=None, description="When projection created")


class TranscriptProjection(BaseModel):
    """Read projection for transcript utterances.

    Materialized from TranscriptParsed events.
    """

    id: int | None = Field(default=None, description="Auto-increment ID")
    meeting_id: str = Field(description="Source meeting UUID")
    speaker: str | None = Field(default=None, description="Speaker name")
    text: str = Field(description="Utterance text")
    start_time: float | None = Field(default=None, description="Start time in seconds")
    created_at: str | None = Field(default=None, description="When projection created")
