"""Meeting model representing a processed meeting transcript."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.base import BaseEntity
from src.models.participant import Participant


class Utterance(BaseModel):
    """A single utterance (speech segment) from the transcript."""

    model_config = ConfigDict(str_strip_whitespace=True)

    speaker: str = Field(description="Speaker name/label from transcript")
    text: str = Field(description="What was said")
    start_time: float = Field(ge=0, description="Start time in seconds")
    end_time: float = Field(ge=0, description="End time in seconds")
    speaker_id: UUID | None = Field(
        default=None,
        description="Resolved participant ID (if identity resolved)",
    )


class Meeting(BaseEntity):
    """A meeting with transcript and extracted artifacts.

    Meetings are the primary aggregate in the system. They contain:
    - Metadata (title, date, duration)
    - Participants (resolved identities)
    - Transcript (utterances)
    - Extracted artifacts are linked via meeting_id in their respective models
    """

    title: str = Field(
        min_length=1,
        max_length=500,
        description="Meeting title (from calendar or transcript)",
    )
    date: datetime = Field(description="When the meeting occurred")
    duration_minutes: int | None = Field(
        default=None,
        ge=0,
        description="Meeting duration in minutes",
    )
    participants: list[Participant] = Field(
        default_factory=list,
        description="Meeting attendees",
    )
    utterances: list[Utterance] = Field(
        default_factory=list,
        description="Transcript broken into utterances",
    )
    transcript_source: str | None = Field(
        default=None,
        description="Source of transcript (zoom, otter, manual)",
    )
    transcript_file: str | None = Field(
        default=None,
        description="Original transcript filename",
    )
    calendar_event_id: str | None = Field(
        default=None,
        description="Google Calendar event ID (if linked)",
    )

    @property
    def speaker_names(self) -> list[str]:
        """Get unique speaker names from utterances."""
        return list({u.speaker for u in self.utterances})

    @property
    def participant_count(self) -> int:
        """Get number of participants."""
        return len(self.participants)

    @property
    def has_transcript(self) -> bool:
        """Check if meeting has transcript content."""
        return len(self.utterances) > 0
