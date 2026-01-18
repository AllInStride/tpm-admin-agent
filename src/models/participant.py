"""Participant model for meeting attendees."""

from enum import Enum

from pydantic import EmailStr, Field, field_validator

from src.models.base import BaseEntity


class ParticipantRole(str, Enum):
    """Role of participant in the meeting."""

    HOST = "host"
    PRESENTER = "presenter"
    ATTENDEE = "attendee"
    GUEST = "guest"


class Participant(BaseEntity):
    """A person who participated in a meeting.

    Participants are identified from:
    - Zoom meeting metadata (calendar invite)
    - Transcript speaker diarization
    - Manual roster mapping
    """

    name: str = Field(
        min_length=1,
        max_length=200,
        description="Display name (from transcript or roster)",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Email address (if resolved from roster)",
    )
    role: ParticipantRole = Field(
        default=ParticipantRole.ATTENDEE,
        description="Role in the meeting",
    )
    external_id: str | None = Field(
        default=None,
        description="ID in external system (Slack, Google, etc.)",
    )
    transcript_name: str | None = Field(
        default=None,
        description="Original name as it appeared in transcript",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for identity resolution (0-1)",
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            msg = "Name cannot be empty or whitespace"
            raise ValueError(msg)
        return v.strip()
