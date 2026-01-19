"""Search module for cross-meeting intelligence.

Provides open item tracking, dashboard queries, item history,
and read projections for full-text search.
"""

from src.search.open_items import (
    CLOSED_STATUSES,
    GroupedOpenItems,
    ItemHistory,
    ItemHistoryEntry,
    OpenItemFilter,
    OpenItemSummary,
    classify_change,
    is_item_open,
)
from src.search.projections import ProjectionBuilder
from src.search.schemas import (
    MeetingProjection,
    RaidItemProjection,
    TranscriptProjection,
)

__all__ = [
    "CLOSED_STATUSES",
    "GroupedOpenItems",
    "ItemHistory",
    "ItemHistoryEntry",
    "MeetingProjection",
    "OpenItemFilter",
    "OpenItemSummary",
    "ProjectionBuilder",
    "RaidItemProjection",
    "TranscriptProjection",
    "classify_change",
    "is_item_open",
]
