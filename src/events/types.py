"""Typed event definitions for domain events.

These events represent things that happen in the system:
- MeetingCreated: A new meeting was created
- TranscriptParsed: Transcript was parsed into utterances
- MeetingProcessed: All extraction completed
- ActionItemExtracted: An action item was extracted
- DecisionExtracted: A decision was extracted
- RiskExtracted: A risk was extracted
- IssueExtracted: An issue was extracted
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.events.base import Event


class MeetingCreated(Event):
    """Emitted when a new meeting is created from transcript upload."""

    aggregate_type: str = "Meeting"
    title: str = Field(description="Meeting title")
    meeting_date: datetime = Field(description="When the meeting occurred")
    participant_count: int = Field(default=0, description="Number of participants")
    transcript_filename: str | None = Field(
        default=None, description="Original transcript filename"
    )


class TranscriptParsed(Event):
    """Emitted when a transcript is successfully parsed."""

    aggregate_type: str = "Meeting"
    utterance_count: int = Field(description="Number of utterances parsed")
    speaker_count: int = Field(description="Number of unique speakers")
    duration_seconds: float | None = Field(
        default=None, description="Total transcript duration"
    )


class MeetingProcessed(Event):
    """Emitted when all extraction is complete for a meeting."""

    aggregate_type: str = "Meeting"
    action_item_count: int = Field(default=0, description="Action items extracted")
    decision_count: int = Field(default=0, description="Decisions extracted")
    risk_count: int = Field(default=0, description="Risks extracted")
    issue_count: int = Field(default=0, description="Issues extracted")
    processing_time_ms: int | None = Field(
        default=None, description="Total processing time in milliseconds"
    )


class ActionItemExtracted(Event):
    """Emitted when an action item is extracted from a transcript."""

    aggregate_type: str = "ActionItem"
    meeting_id: UUID = Field(description="ID of source meeting")
    action_item_id: UUID = Field(description="ID of the created action item")
    description: str = Field(description="Action item description")
    assignee_name: str | None = Field(
        default=None, description="Assigned person (as mentioned)"
    )
    due_date: datetime | None = Field(default=None, description="Due date if specified")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )


class DecisionExtracted(Event):
    """Emitted when a decision is extracted from a transcript."""

    aggregate_type: str = "Decision"
    meeting_id: UUID = Field(description="ID of source meeting")
    decision_id: UUID = Field(description="ID of the created decision")
    description: str = Field(description="Decision description")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )


class RiskExtracted(Event):
    """Emitted when a risk is extracted from a transcript."""

    aggregate_type: str = "Risk"
    meeting_id: UUID = Field(description="ID of source meeting")
    risk_id: UUID = Field(description="ID of the created risk")
    description: str = Field(description="Risk description")
    severity: str = Field(description="Severity level")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )


class IssueExtracted(Event):
    """Emitted when an issue is extracted from a transcript."""

    aggregate_type: str = "Issue"
    meeting_id: UUID = Field(description="ID of source meeting")
    issue_id: UUID = Field(description="ID of the created issue")
    description: str = Field(description="Issue description")
    priority: str = Field(description="Priority level")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )
