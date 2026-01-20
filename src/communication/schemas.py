"""Schemas for communication artifact generation.

Defines output schemas for all four artifact types:
- Exec status updates (COM-01)
- Team status updates (COM-02)
- Escalation emails (COM-03)
- Exec talking points (COM-04)
"""

from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field


@dataclass
class StatusData:
    """Aggregated data for status generation.

    Contains all data needed to generate status updates,
    gathered from repositories before LLM synthesis.
    """

    project_id: str
    time_period: tuple[datetime, datetime]

    # Progress
    completed_items: list[dict] = field(default_factory=list)
    new_items: list[dict] = field(default_factory=list)
    open_items: list[dict] = field(default_factory=list)

    # RAID summary
    decisions: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    blockers: list[dict] = field(default_factory=list)

    # Meetings
    meetings_held: list[dict] = field(default_factory=list)

    # Metrics
    item_velocity: int = 0
    overdue_count: int = 0


class ExecStatusOutput(BaseModel):
    """LLM-generated exec status content.

    Per CONTEXT.md:
    - Half page (5-7 bullet points with context)
    - Reference teams, not individuals
    - Include RAG indicator breakdown (overall + scope/schedule/risk)
    - Blockers framed as: problem + explicit ask from exec
    - Include "next period" lookahead section
    """

    overall_rag: str = Field(description="Overall status: GREEN, AMBER, or RED")
    scope_rag: str = Field(description="Scope status: GREEN, AMBER, or RED")
    schedule_rag: str = Field(description="Schedule status: GREEN, AMBER, or RED")
    risk_rag: str = Field(description="Risk status: GREEN, AMBER, or RED")

    summary: str = Field(description="2-3 sentence executive summary")

    key_progress: list[str] = Field(
        description="3-5 key progress highlights (team references, not names)"
    )

    key_decisions: list[str] = Field(
        default_factory=list, description="Key decisions made this period"
    )

    blockers: list[dict] = Field(
        default_factory=list,
        description="Blockers with title, problem, and explicit ask from exec",
    )

    risks: list[str] = Field(
        default_factory=list, description="Active risks requiring awareness"
    )

    next_period: list[str] = Field(description="3-5 items expected next period")


class TeamStatusOutput(BaseModel):
    """LLM-generated team status content.

    Per CONTEXT.md:
    - Full list of action items with owners and due dates
    - Much more detailed than exec version
    - Meeting notes aggregated
    - Include "completed items" section to celebrate wins
    """

    summary: str = Field(description="Brief summary of team progress this period")

    completed_items: list[dict] = Field(
        default_factory=list,
        description="Items completed this period (description, owner, completed_date)",
    )

    open_items: list[dict] = Field(
        default_factory=list,
        description="Open items with description, owner, due_date, status",
    )

    decisions: list[str] = Field(
        default_factory=list, description="Decisions made this period"
    )

    risks: list[str] = Field(default_factory=list, description="Active risks")

    issues: list[str] = Field(default_factory=list, description="Open issues")


class EscalationOutput(BaseModel):
    """LLM-generated escalation email content.

    Per CONTEXT.md:
    - Problem-Impact-Ask format
    - Explicit deadline ("Decision needed by [date]")
    - Always include options (A, B, or C)
    - Tone: matter-of-fact (facts only, no emotional language)
    """

    subject: str = Field(description="Email subject line (clear, specific)")

    problem: str = Field(description="Clear statement of the problem (2-3 sentences)")

    impact: str = Field(description="Business/project impact if not resolved")

    deadline: str = Field(description="When decision is needed (specific date)")

    options: list[dict] = Field(
        description="2-3 options with label, description, pros, cons"
    )

    recommendation: str | None = Field(
        default=None, description="Recommended option if appropriate"
    )

    context_summary: str | None = Field(
        default=None, description="Brief history if relevant (1-2 sentences)"
    )


class TalkingPointsOutput(BaseModel):
    """LLM-generated exec talking points.

    Per CONTEXT.md:
    - Key bullet points + anticipated Q&A section
    - Focus on narrative/story with supporting data
    - Comprehensive Q&A coverage (risk/concern + resource + other)
    """

    narrative_summary: str = Field(description="High-level narrative summary for exec")

    key_points: list[str] = Field(description="Key talking points (5-7 bullets)")

    anticipated_qa: list[dict] = Field(
        description="Anticipated Q&A with category, question, answer"
    )


class GeneratedArtifact(BaseModel):
    """Output from artifact generation.

    Contains both markdown and plain text versions
    for flexible delivery (email, Slack, wiki).
    """

    artifact_type: str = Field(
        description="Type: exec_status, team_status, escalation, talking_points"
    )

    markdown: str = Field(description="Markdown-formatted output")

    plain_text: str = Field(description="Plain text output (for email/Slack)")

    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (RAG status, counts, etc.)",
    )


class EscalationRequest(BaseModel):
    """Request to generate an escalation email.

    User provides problem details and options;
    generator creates Problem-Impact-Ask formatted email.
    """

    problem_description: str = Field(
        description="Description of the problem requiring escalation"
    )

    timeline_impact: str | None = Field(
        default=None, description="Impact on project timeline"
    )

    resource_impact: str | None = Field(
        default=None, description="Impact on resources/budget"
    )

    business_impact: str | None = Field(
        default=None, description="Business impact if not resolved"
    )

    history_context: str | None = Field(
        default=None, description="Brief history if relevant"
    )

    options: list[dict] = Field(
        description="Options for recipient with description, pros, cons"
    )

    decision_deadline: datetime = Field(description="When decision is needed")

    recipient: str | None = Field(
        default=None, description="Intended recipient (name or email)"
    )
