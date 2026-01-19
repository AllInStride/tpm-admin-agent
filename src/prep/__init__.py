"""Meeting prep module.

Provides proactive meeting preparation with open item surfacing,
context gathering, and summary generation.
"""

from src.prep.context_gatherer import (
    ContextGatherer,
    PrepContext,
    normalize_series_key,
)
from src.prep.item_matcher import (
    ItemMatcher,
    generate_talking_points,
    prioritize_items,
)
from src.prep.schemas import (
    CalendarEvent,
    MeetingPrepRequest,
    PrepConfig,
    PrepItem,
    PrepSummary,
    TalkingPoint,
)

__all__ = [
    "CalendarEvent",
    "ContextGatherer",
    "ItemMatcher",
    "MeetingPrepRequest",
    "PrepConfig",
    "PrepContext",
    "PrepItem",
    "PrepSummary",
    "TalkingPoint",
    "generate_talking_points",
    "normalize_series_key",
    "prioritize_items",
]
