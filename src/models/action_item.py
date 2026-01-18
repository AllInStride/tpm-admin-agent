"""ActionItem model for tasks extracted from meetings."""

from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import Field

from src.models.base import BaseEntity


class ActionItemStatus(str, Enum):
    """Status of an action item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ActionItem(BaseEntity):
    """An action item extracted from a meeting.

    Action items are commitments made during meetings with:
    - A description of what needs to be done
    - An assignee (who committed to do it)
    - A due date (when it should be done)
    - Status tracking
    """

    meeting_id: UUID = Field(description="Meeting this action item was extracted from")
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="What needs to be done",
    )
    assignee_name: str | None = Field(
        default=None,
        description="Name of person assigned (from transcript)",
    )
    assignee_id: UUID | None = Field(
        default=None,
        description="Resolved participant ID (if identity resolved)",
    )
    due_date: date | None = Field(
        default=None,
        description="When the action item is due",
    )
    status: ActionItemStatus = Field(
        default=ActionItemStatus.PENDING,
        description="Current status",
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
        description="ID in external system (Smartsheet, Jira, etc.)",
    )

    @property
    def is_assigned(self) -> bool:
        """Check if action item has an assignee."""
        return self.assignee_name is not None or self.assignee_id is not None

    @property
    def is_overdue(self) -> bool:
        """Check if action item is past due date."""
        if self.due_date is None:
            return False
        if self.status in (ActionItemStatus.COMPLETED, ActionItemStatus.CANCELLED):
            return False
        return date.today() > self.due_date
