"""Risk model for risks identified during meetings."""

from enum import Enum
from uuid import UUID

from pydantic import Field

from src.models.base import BaseEntity


class RiskSeverity(str, Enum):
    """Severity level of a risk."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Risk(BaseEntity):
    """A risk identified during a meeting.

    Risks are potential problems that might occur. They're tracked to:
    - Enable proactive mitigation
    - Provide early warning for project health
    - Roll up to director/VP level views
    """

    meeting_id: UUID = Field(description="Meeting this risk was extracted from")
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Description of the risk",
    )
    severity: RiskSeverity = Field(
        default=RiskSeverity.MEDIUM,
        description="Severity level",
    )
    impact: str | None = Field(
        default=None,
        max_length=1000,
        description="Potential impact if risk materializes",
    )
    mitigation: str | None = Field(
        default=None,
        max_length=1000,
        description="Proposed mitigation strategy",
    )
    owner_name: str | None = Field(
        default=None,
        description="Name of risk owner (from transcript)",
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
    is_mitigated: bool = Field(
        default=False,
        description="Whether mitigation has been implemented",
    )

    @property
    def is_high_severity(self) -> bool:
        """Check if risk is high or critical severity."""
        return self.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)

    @property
    def has_mitigation(self) -> bool:
        """Check if risk has a mitigation plan."""
        return self.mitigation is not None and len(self.mitigation.strip()) > 0
