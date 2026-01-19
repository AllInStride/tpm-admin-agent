"""Output schemas for meeting minutes rendering."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.action_item import ActionItem
from src.models.decision import Decision
from src.models.issue import Issue
from src.models.meeting import Meeting
from src.models.risk import Risk


class DecisionItem(BaseModel):
    """Decision data for template rendering (flattened from domain model)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(description="What was decided")
    rationale: str | None = Field(default=None, description="Why decided")
    alternatives: list[str] = Field(
        default_factory=list, description="Alternatives considered"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )


class ActionItemData(BaseModel):
    """Action item data for template rendering."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(description="What needs to be done")
    assignee_name: str | None = Field(default=None, description="Who is responsible")
    due_date: str | None = Field(default=None, description="Due date or TBD")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )


class RiskItem(BaseModel):
    """Risk data for template rendering."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(description="Risk description")
    severity: str = Field(default="MEDIUM", description="Severity (uppercase)")
    owner_name: str | None = Field(default=None, description="Risk owner")
    mitigation: str | None = Field(default=None, description="Mitigation plan")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )


class IssueItem(BaseModel):
    """Issue data for template rendering."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(description="Issue description")
    priority: str = Field(default="MEDIUM", description="Priority (uppercase)")
    status: str = Field(default="Open", description="Current status")
    owner_name: str | None = Field(default=None, description="Issue owner")
    impact: str | None = Field(default=None, description="Impact description")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence"
    )


class MinutesContext(BaseModel):
    """Context data for rendering meeting minutes templates.

    This is the main input to the MinutesRenderer. It contains all
    meeting data in a template-friendly format.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    meeting_id: UUID = Field(description="Unique meeting identifier")
    meeting_title: str = Field(description="Meeting title")
    meeting_date: datetime = Field(description="When the meeting occurred")
    duration_minutes: int | None = Field(default=None, description="Meeting duration")
    attendees: list[str] = Field(
        default_factory=list,
        description="Names with roles, e.g., 'John Smith (PM)'",
    )
    decisions: list[DecisionItem] = Field(default_factory=list)
    action_items: list[ActionItemData] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    issues: list[IssueItem] = Field(default_factory=list)
    next_steps: list[str] = Field(
        default_factory=list,
        description="Top 3-5 action item descriptions",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When minutes were generated",
    )

    @classmethod
    def from_meeting_data(
        cls,
        meeting: Meeting,
        decisions: list[Decision],
        action_items: list[ActionItem],
        risks: list[Risk],
        issues: list[Issue],
    ) -> "MinutesContext":
        """Convert domain models to template-friendly context.

        Args:
            meeting: Meeting domain model
            decisions: List of Decision domain models
            action_items: List of ActionItem domain models
            risks: List of Risk domain models
            issues: List of Issue domain models

        Returns:
            MinutesContext ready for template rendering
        """
        # Format attendees with roles if available
        attendees = []
        for participant in meeting.participants:
            if participant.role:
                role_str = participant.role.value.title()
                attendees.append(f"{participant.name} ({role_str})")
            else:
                attendees.append(participant.name)

        # Convert decisions
        decision_items = [
            DecisionItem(
                description=d.description,
                rationale=d.rationale,
                alternatives=d.alternatives,
                confidence=d.confidence,
            )
            for d in decisions
        ]

        # Convert action items with formatted due dates
        action_data = []
        for ai in action_items:
            due_date_str = ai.due_date.strftime("%Y-%m-%d") if ai.due_date else None
            action_data.append(
                ActionItemData(
                    description=ai.description,
                    assignee_name=ai.assignee_name,
                    due_date=due_date_str,
                    confidence=ai.confidence,
                )
            )

        # Convert risks
        risk_items = [
            RiskItem(
                description=r.description,
                severity=r.severity.value.upper(),
                owner_name=r.owner_name,
                mitigation=r.mitigation,
                confidence=r.confidence,
            )
            for r in risks
        ]

        # Convert issues
        issue_items = [
            IssueItem(
                description=i.description,
                priority=i.priority.value.upper(),
                status=i.status.value.replace("_", " ").title(),
                owner_name=i.owner_name,
                impact=i.impact,
                confidence=i.confidence,
            )
            for i in issues
        ]

        # Generate next_steps from top 3-5 action items
        next_steps = [ai.description for ai in action_items[:5]]

        return cls(
            meeting_id=meeting.id,
            meeting_title=meeting.title,
            meeting_date=meeting.date,
            duration_minutes=meeting.duration_minutes,
            attendees=attendees,
            decisions=decision_items,
            action_items=action_data,
            risks=risk_items,
            issues=issue_items,
            next_steps=next_steps,
        )


class RenderedMinutes(BaseModel):
    """Result of rendering meeting minutes."""

    model_config = ConfigDict(str_strip_whitespace=True)

    meeting_id: UUID = Field(description="Meeting these minutes are for")
    markdown: str = Field(description="Rendered Markdown content")
    html: str = Field(description="Rendered HTML content")
    template_used: str = Field(description="Template name used for rendering")


class RaidBundle(BaseModel):
    """Bundle of RAID items for passing to Sheets adapter."""

    model_config = ConfigDict(str_strip_whitespace=True)

    meeting_id: UUID = Field(description="Meeting these items are from")
    decisions: list[DecisionItem] = Field(default_factory=list)
    action_items: list[ActionItemData] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    issues: list[IssueItem] = Field(default_factory=list)
