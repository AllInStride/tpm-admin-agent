"""Identity resolution schemas.

Defines data models for roster entries and resolution results.
"""

from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class RosterEntry(BaseModel):
    """Person in project roster from Google Sheets.

    Represents a single row from the roster spreadsheet.
    Email is the unique identifier across all systems.
    """

    name: str = Field(description="Full name")
    email: EmailStr = Field(description="Email - unique identifier")
    slack_handle: str | None = Field(default=None, description="Slack @handle")
    role: str | None = Field(default=None, description="Role on project")
    aliases: list[str] = Field(
        default_factory=list,
        description="Known nicknames/variations (from Aliases column)",
    )

    @classmethod
    def from_sheet_row(cls, row: dict) -> "RosterEntry":
        """Parse from Google Sheets row.

        Expected columns: Name, Email, Slack handle (optional),
        Role (optional), Aliases (optional, comma-separated).

        Args:
            row: Dictionary of column name -> value from sheet row

        Returns:
            RosterEntry parsed from row data
        """
        aliases: list[str] = []
        if alias_str := row.get("Aliases", ""):
            aliases = [a.strip() for a in alias_str.split(",") if a.strip()]
        return cls(
            name=row["Name"],
            email=row["Email"],
            slack_handle=row.get("Slack handle"),
            role=row.get("Role"),
            aliases=aliases,
        )


class ResolutionSource(str, Enum):
    """How a name match was determined."""

    EXACT = "exact"
    LEARNED = "learned"
    FUZZY = "fuzzy"
    LLM = "llm"
    CALENDAR = "calendar"
    SLACK = "slack"


class ResolutionResult(BaseModel):
    """Result of name resolution attempt.

    Tracks the original transcript name, the resolved identity (if any),
    confidence score, and how the match was determined.
    """

    transcript_name: str = Field(description="Original name from transcript")
    resolved_email: str | None = Field(
        default=None, description="Matched person's email"
    )
    resolved_name: str | None = Field(default=None, description="Canonical name")
    confidence: float = Field(ge=0.0, le=1.0, description="Match confidence (0-1)")
    source: ResolutionSource = Field(description="How match was determined")
    alternatives: list[tuple[str, float]] = Field(
        default_factory=list,
        description="Other possible matches with scores [(name, score), ...]",
    )
    requires_review: bool = Field(
        default=True, description="True if confidence < 0.85 (needs human confirmation)"
    )

    @property
    def is_resolved(self) -> bool:
        """Check if name was successfully resolved.

        A name is resolved if we have an email match with confidence >= 85%.
        Below this threshold, human review is required.
        """
        return self.resolved_email is not None and self.confidence >= 0.85
