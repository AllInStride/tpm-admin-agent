"""Decision model for decisions extracted from meetings."""

from uuid import UUID

from pydantic import Field

from src.models.base import BaseEntity


class Decision(BaseEntity):
    """A decision made during a meeting.

    Decisions are captured to:
    - Prevent "decision amnesia" (relitigating settled issues)
    - Provide audit trail for why things were done
    - Track alternatives that were considered
    """

    meeting_id: UUID = Field(description="Meeting this decision was extracted from")
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="What was decided",
    )
    rationale: str | None = Field(
        default=None,
        max_length=2000,
        description="Why this decision was made",
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description="Alternatives that were considered",
    )
    participants: list[UUID] = Field(
        default_factory=list,
        description="Participants involved in the decision",
    )
    source_quote: str | None = Field(
        default=None,
        max_length=1000,
        description="Original quote from transcript",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for extraction (0-1)",
    )
    external_id: str | None = Field(
        default=None,
        description="ID in external system (if synced)",
    )

    @property
    def has_rationale(self) -> bool:
        """Check if decision has documented rationale."""
        return self.rationale is not None and len(self.rationale.strip()) > 0

    @property
    def alternatives_count(self) -> int:
        """Get number of alternatives considered."""
        return len(self.alternatives)
