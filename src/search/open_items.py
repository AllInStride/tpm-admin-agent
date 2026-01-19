"""Open item definition and dashboard schemas.

Provides single source of truth for "open" definition and schemas
for dashboard queries and item tracking.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# Single source of truth for closed statuses
CLOSED_STATUSES = frozenset({"completed", "cancelled", "closed", "resolved"})


def is_item_open(status: str | None) -> bool:
    """Single source of truth for 'open' definition.

    An item is open if its status is not in the closed set.
    Items with None status are considered open (default state).

    Args:
        status: Item status string or None

    Returns:
        True if item is open, False if closed
    """
    if status is None:
        return True
    return status.lower() not in CLOSED_STATUSES


def classify_change(event_type: str) -> str:
    """Classify event into change type for timeline display.

    Args:
        event_type: Event type string (e.g., ActionItemExtracted)

    Returns:
        Change classification: 'created', 'updated', or 'mentioned'
    """
    if "Extracted" in event_type:
        return "created"
    if "Updated" in event_type:
        return "updated"
    return "mentioned"


class OpenItemFilter(BaseModel):
    """Filter criteria for open items queries."""

    item_type: str | None = Field(
        default=None,
        description="Filter by item type: action, decision, risk, issue",
    )
    owner: str | None = Field(
        default=None,
        description="Filter by item owner name",
    )
    meeting_id: str | None = Field(
        default=None,
        description="Filter by meeting ID",
    )
    overdue_only: bool = Field(
        default=False,
        description="Only return overdue items",
    )
    due_within_days: int | None = Field(
        default=None,
        description="Filter items due within N days (e.g., 7 for this week)",
        ge=0,
    )


class OpenItemSummary(BaseModel):
    """Summary counts for open items dashboard."""

    total: int = Field(description="Total open items")
    overdue: int = Field(description="Items past due date")
    due_today: int = Field(description="Items due today")
    due_this_week: int = Field(description="Items due within 7 days (excluding today)")
    by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count by item type (action, decision, risk, issue)",
    )


class GroupedOpenItems(BaseModel):
    """Open items with summary and grouping."""

    summary: OpenItemSummary = Field(description="Summary counts")
    items: list[dict] = Field(
        default_factory=list,
        description="Raw item dicts with all fields",
    )
    group_by: str = Field(
        default="due_date",
        description="Grouping key: due_date, owner, or item_type",
    )


class ItemHistoryEntry(BaseModel):
    """Single entry in an item's history timeline."""

    timestamp: datetime = Field(description="When this event occurred")
    event_type: str = Field(description="Event type that caused this entry")
    change_type: str = Field(
        description="Change classification: created, updated, mentioned"
    )
    meeting_id: str | None = Field(default=None, description="Related meeting ID")
    meeting_title: str | None = Field(default=None, description="Related meeting title")
    meeting_date: str | None = Field(default=None, description="Related meeting date")


class ItemHistory(BaseModel):
    """Complete history of an item across meetings."""

    item_id: str = Field(description="Item identifier")
    item_type: str = Field(description="Item type: action, decision, risk, issue")
    description: str = Field(description="Current item description")
    current_status: str = Field(description="Current status")
    entries: list[ItemHistoryEntry] = Field(
        default_factory=list,
        description="Chronological list of history entries",
    )
