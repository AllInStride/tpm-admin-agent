"""Pydantic models for LLM extraction output.

These schemas define the structure that the LLM returns when extracting
RAID items from transcripts. They are intentionally different from domain
models because:
- due_date_raw is a string (normalized to date later)
- No UUIDs (LLM doesn't generate these)
- No timestamps (added during domain conversion)
- No external_ids (assigned after extraction)
"""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedActionItem(BaseModel):
    """Schema for LLM extraction of action items."""

    description: str = Field(
        description="What needs to be done - clear, actionable statement"
    )
    assignee_name: str | None = Field(
        default=None,
        description="Name of person assigned, exactly as mentioned in transcript",
    )
    due_date_raw: str | None = Field(
        default=None,
        description="Due date as mentioned (e.g., 'next Friday', 'end of month')",
    )
    source_quote: str = Field(
        description="Exact quote from transcript supporting this action item"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence this is a real action item (0.0-1.0)",
    )


class ExtractedActionItems(BaseModel):
    """Container for multiple extracted action items."""

    items: list[ExtractedActionItem] = Field(
        default_factory=list,
        description="List of extracted action items",
    )


class ExtractedDecision(BaseModel):
    """Schema for LLM extraction of decisions."""

    description: str = Field(
        description="What was decided - clear statement of the choice made"
    )
    rationale: str | None = Field(
        default=None,
        description="Why this decision was made, if discussed",
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description="Other options that were considered",
    )
    source_quote: str = Field(
        description="Exact quote from transcript where this decision was made"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence this is a finalized decision (0.0-1.0)",
    )


class ExtractedDecisions(BaseModel):
    """Container for multiple extracted decisions."""

    items: list[ExtractedDecision] = Field(
        default_factory=list,
        description="List of extracted decisions",
    )


class ExtractedRisk(BaseModel):
    """Schema for LLM extraction of risks."""

    description: str = Field(description="What the risk is - what might go wrong")
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="How severe if it materializes"
    )
    impact: str | None = Field(
        default=None,
        description="What happens if this risk materializes",
    )
    mitigation: str | None = Field(
        default=None,
        description="How to prevent or reduce this risk",
    )
    owner_name: str | None = Field(
        default=None,
        description="Name of person responsible for this risk, exactly as mentioned",
    )
    source_quote: str = Field(
        description="Exact quote from transcript where this risk was mentioned"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence this is a real risk being raised (0.0-1.0)",
    )


class ExtractedRisks(BaseModel):
    """Container for multiple extracted risks."""

    items: list[ExtractedRisk] = Field(
        default_factory=list,
        description="List of extracted risks",
    )


class ExtractedIssue(BaseModel):
    """Schema for LLM extraction of issues."""

    description: str = Field(description="What the issue is - what is currently wrong")
    priority: Literal["low", "medium", "high", "critical"] = Field(
        description="How urgent to address"
    )
    status: Literal["open"] = Field(
        default="open",
        description="Status of newly identified issues (always 'open')",
    )
    impact: str | None = Field(
        default=None,
        description="How this issue is affecting the project",
    )
    owner_name: str | None = Field(
        default=None,
        description="Name of person responsible for resolving, exactly as mentioned",
    )
    source_quote: str = Field(
        description="Exact quote from transcript where this issue was raised"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence this is a real issue being raised (0.0-1.0)",
    )


class ExtractedIssues(BaseModel):
    """Container for multiple extracted issues."""

    items: list[ExtractedIssue] = Field(
        default_factory=list,
        description="List of extracted issues",
    )
