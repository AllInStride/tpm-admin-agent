"""Issue model for issues identified during meetings."""

from enum import Enum
from uuid import UUID

from pydantic import Field

from src.models.base import BaseEntity


class IssuePriority(str, Enum):
    """Priority level of an issue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, Enum):
    """Status of an issue."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Issue(BaseEntity):
    """An issue identified during a meeting.

    Issues are current problems (unlike risks which are potential).
    They're tracked to:
    - Ensure blockers get addressed
    - Provide visibility to leadership
    - Track resolution progress
    """

    meeting_id: UUID = Field(description="Meeting this issue was extracted from")
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Description of the issue",
    )
    status: IssueStatus = Field(
        default=IssueStatus.OPEN,
        description="Current status",
    )
    priority: IssuePriority = Field(
        default=IssuePriority.MEDIUM,
        description="Priority level",
    )
    impact: str | None = Field(
        default=None,
        max_length=1000,
        description="Impact of the issue on the project",
    )
    resolution: str | None = Field(
        default=None,
        max_length=1000,
        description="How the issue was or will be resolved",
    )
    owner_name: str | None = Field(
        default=None,
        description="Name of issue owner (from transcript)",
    )
    owner_id: UUID | None = Field(
        default=None,
        description="Resolved participant ID (if identity resolved)",
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
    def is_blocking(self) -> bool:
        """Check if issue is currently blocking progress."""
        return self.status == IssueStatus.BLOCKED

    @property
    def is_high_priority(self) -> bool:
        """Check if issue is high or critical priority."""
        return self.priority in (IssuePriority.HIGH, IssuePriority.CRITICAL)

    @property
    def is_resolved(self) -> bool:
        """Check if issue has been resolved or closed."""
        return self.status in (IssueStatus.RESOLVED, IssueStatus.CLOSED)
