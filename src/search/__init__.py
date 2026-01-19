"""Search module for cross-meeting intelligence.

Provides open item tracking, dashboard queries, item history,
full-text search, and read projections.
"""

from src.search.fts_service import (
    FTSService,
    ParsedQuery,
    SearchResponse,
    SearchResult,
    parse_search_query,
)
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
    "FTSService",
    "GroupedOpenItems",
    "ItemHistory",
    "ItemHistoryEntry",
    "MeetingProjection",
    "OpenItemFilter",
    "OpenItemSummary",
    "ParsedQuery",
    "ProjectionBuilder",
    "RaidItemProjection",
    "SearchResponse",
    "SearchResult",
    "TranscriptProjection",
    "classify_change",
    "is_item_open",
    "parse_search_query",
]
